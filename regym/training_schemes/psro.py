'''
Implementation of Policy-Spaced Response Oracles (PSRO) as first introduced in Lanctot et al 2017:
http://papers.nips.cc/paper/7007-a-unified-game-theoretic-approach-to-multiagent-reinforcement-learning

TODO: difference between PSRO which takes 3 separate stages and our method, which is an online method.
'''
from recordclass import recordclass
import logging
import time
from typing import Callable, List
from itertools import product
import numpy as np

from regym.rl_algorithms import AgentHook
from regym.game_theory import compute_nash_averaging
from regym.util import play_multiple_matches
from regym.util import extract_winner
from regym.environments import generate_task


class PSRONashResponse():

    IterationStatistics = recordclass('IterationStatistics', [
                                      'total_elapsed_episodes',
                                      'current_iteration_elapsed_episodes',
                                      'menagerie_picks',
                                      'meta_game_solution'])

    def __init__(self,
                 env_id: str,
                 meta_game_solver: Callable = lambda winrate_matrix: compute_nash_averaging(winrate_matrix, perform_logodds_transformation=True)[0],
                 threshold_best_response: float = 0.7,
                 benchmarking_episodes: int = 10,
                 match_outcome_rolling_window_size: int = 10):
        '''
        :param env_id: Environment identifier from which to create an environment
        :param meta_game_solver: Function which takes a meta-game and returns a probability
                                 distribution over the policies in the meta-game.
                                 Default uses maxent-Nash equilibrium for the logodds transformation
                                 of the winrate_matrix metagame.
        :param threshold_best_response: Winrate thrshold after which the agent being
                                        trained is to converge towards a best response
                                        againts the current meta-game solution.
        :param benchmarking_episodes: Number of episodes that will be used to compute winrates
                                      to fill the metagame.
        :param match_outcome_rolling_window_size: Number of episodes that will be used to
                                                  decide whether the currently training agent
                                                  has converged to a best response.
        '''
        self.name = 'PSRO_M=maxent-Nash_O=BestResponse'
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        self.check_parameter_validity(env_id, threshold_best_response,
                                      benchmarking_episodes,
                                      match_outcome_rolling_window_size)
        self.env_id = env_id

        self.meta_game_solver = meta_game_solver
        self.meta_game = None
        self.meta_game_solution = None
        self.menagerie = []

        self.threshold_best_response = threshold_best_response
        self.match_outcome_rolling_window = []
        self.match_outcome_rolling_window_size = match_outcome_rolling_window_size

        self.benchmarking_episodes = benchmarking_episodes

        self.statistics = [self.IterationStatistics(0, 0, [0], np.nan)]

    def opponent_sampling_distribution(self, menagerie, training_agent):
        '''
        :param menagerie: archive of agents selected by the curator and the potential opponents
        :param training_agent: Agent currently being trained
        '''
        if len(menagerie) == 0 and len(self.menagerie) == 0:
            self.init_meta_game_and_solution(training_agent)
        sampled_index = np.random.choice([i for i in range(len(self.menagerie))],
                                         p=self.meta_game_solution)
        self.statistics[-1].menagerie_picks[sampled_index] += 1
        return [self.menagerie[sampled_index]]

    def init_meta_game_and_solution(self, training_agent):
        self.add_agent_to_menagerie(training_agent)
        self.meta_game = np.array([[0.5]])
        self.meta_game_solution = np.array([1.0])

    def curator(self, menagerie, training_agent, episode_trajectory,
                training_agent_index, candidate_save_path):
        '''
        :param menagerie: archive of agents selected by the curator and the potential opponents
        :param training_agent: AgentHook of the Agent currently being trained
        :returns: menagerie to be used in the next training episode.
        '''
        self.statistics[-1].total_elapsed_episodes += 1
        self.statistics[-1].current_iteration_elapsed_episodes += 1

        self.update_rolling_winrates(episode_trajectory, training_agent_index)
        if self.has_policy_converged():
            self.add_agent_to_menagerie(training_agent, candidate_save_path)
            self.update_meta_game()
            self.update_meta_game_solution()
            self.match_outcome_rolling_window = []
            self.statistics += [self.create_new_iteration_statistics(self.statistics[-1])]
            self.statistics[-1].meta_game_solution = self.meta_game_solution
        return self.menagerie

    def has_policy_converged(self):
        current_winrate = (sum(self.match_outcome_rolling_window) \
                           / self.match_outcome_rolling_window_size)
        return current_winrate >= self.threshold_best_response

    def update_rolling_winrates(self, episode_trajectory, training_agent_index):
        winner_index = extract_winner(episode_trajectory)
        victory = int(winner_index == training_agent_index)
        if len(self.match_outcome_rolling_window) >= self.match_outcome_rolling_window_size:
            self.match_outcome_rolling_window.pop(0)
        self.match_outcome_rolling_window.append(victory)

    def update_meta_game_solution(self, update=False):
        self.logger.debug(f'START: Solving metagame. Size: {len(self.menagerie)}')
        start_time = time.time()
        self.meta_game_solution = self.meta_game_solver(self.meta_game)
        time_elapsed = time.time() - start_time
        self.logger.debug(f'FINISH: Solving metagame. time: {time_elapsed}')
        return self.meta_game_solution

    def update_meta_game(self):
        self.logger.debug(f'START: updating metagame. Size: {len(self.menagerie)}')
        start_time = time.time()
        number_old_policies = len(self.menagerie) - 1
        updated_meta_game = np.full(((len(self.menagerie)), len(self.menagerie)),
                                    np.nan)

        # Filling the matrix with already-known values.
        updated_meta_game[:number_old_policies, :number_old_policies] = self.meta_game

        self.fill_meta_game_missing_entries(self.menagerie, updated_meta_game, self.benchmarking_episodes,
                                            self.env_id)
        self.meta_game = updated_meta_game
        time_elapsed = time.time() - start_time
        self.logger.debug(f'FINISH: updating metagame. time: {time_elapsed}')
        return updated_meta_game

    def fill_meta_game_missing_entries(self, policies: List,
                                       updated_meta_game: np.ndarray,
                                       benchmarking_episodes: int, env_id: str):
        indices_to_fill = product(range(updated_meta_game.shape[0]),
                                  [updated_meta_game.shape[0] - 1])
        for i, j in indices_to_fill:
            if i == j: updated_meta_game[j, j] = 0.5
            else:
                winrate_estimate = play_multiple_matches(env=generate_task(env_id).env,
                                                         agent_vector=[policies[i],
                                                                       policies[j]],
                                                         n_matches=benchmarking_episodes)[0]
                updated_meta_game[i, j] = winrate_estimate
                updated_meta_game[j, i] = 1 - winrate_estimate
        return updated_meta_game

    def add_agent_to_menagerie(self, training_agent, candidate_save_path=None):
        if candidate_save_path is not None:
            AgentHook(training_agent, save_path=candidate_save_path)
        self.menagerie.append(training_agent.clone(training=False))

    def create_new_iteration_statistics(self, last_iteration_statistics):
        return self.IterationStatistics(last_iteration_statistics.total_elapsed_episodes,
                                        0, [0] * len(self.menagerie),
                                        self.meta_game_solution)

    def check_parameter_validity(self, env_id, threshold_best_response,
                                 benchmarking_episodes,
                                 match_outcome_rolling_window_size):
        try:
            generate_task(env_id)
        except ValueError:
            raise ValueError(f'Unable to generate task from env_id: {env_id} ' +
                             'Provide a registered environment. Refer to regym.environments.parse_environment ' +
                             'documentation.')
        if not(0 <= threshold_best_response <= 1):
            raise ValueError('Parameter \'threshold_best_response\' represents ' +
                             'a winrate (a probability). It must lie between [0, 1]')
        if not(0 < benchmarking_episodes):
            raise ValueError('Parameter \'benchmarking_episodes\' must be strictly positive')
        if not(0 < match_outcome_rolling_window_size):
            raise ValueError('Parameter \'benchmarking_episodes\' corresponds to ' +
                             'the lenght of a list. It must be strictly positive')