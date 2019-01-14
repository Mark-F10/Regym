import time
import logging
import random
import numpy as np
from collections import namedtuple
BenchMarkStatistics = namedtuple('BenchMarkStatistics', 'iteration recorded_policy_vector winrates')

from multiprocessing import Process
from concurrent.futures import as_completed

from multiagent_loops.simultaneous_action_rl_loop import run_episode


def benchmark_match_play_process(num_episodes, createNewEnvironment, benchmark_job, process_pool, matrix_queue, name):
    """
    :param num_episodes: Number of episodes used for stats collection
    :param createNewEnvironment OpenAI gym environment creation function
    :param benchmark_job: BenchmarkingJob containing iteration and policy vector to benchmark
    :param process_pool: ProcessPoolExecutor used to submit match runs jobs
    :param matrix_queue: Queue to which submit stats
    :param name: String identifying this benchmarking process
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.info('Started for {} episodes'.format(num_episodes))

    policy_vector = [recorded_policy.policy for recorded_policy in benchmark_job.recorded_policy_vector]
    winrates = benchmark_policies(policy_vector, createNewEnvironment, num_episodes, logger)

    matrix_queue.put(BenchMarkStatistics(benchmark_job.iteration,
                                         benchmark_job.recorded_policy_vector,
                                         winrates))


def benchmark_policies(policy_vector, createNewEnvironment, num_episodes, logger):
    wins_vector = [0 for _ in range(len(policy_vector))]

    benchmark_start = time.time()
    for i in range(num_episodes):
        episode_winner = single_match(createNewEnvironment(), policy_vector)
        wins_vector[episode_winner] += 1
    benchmark_duration = time.time() - benchmark_start
    logger.info('Benchmarking finished. Duration: {} seconds'.format(benchmark_duration))

    winrates = [winrate / num_episodes for winrate in wins_vector]
    return winrates


def single_match(env, policy_vector):
    # trajectory: [(s,a,r,s')]
    trajectory = run_episode(env, policy_vector, training=False)
    reward_vector = lambda t: t[2]
    individal_policy_trajectory_reward = lambda t, agent_index: sum(map(lambda experience: reward_vector(experience)[agent_index], t))
    cumulative_reward_vector = [individal_policy_trajectory_reward(trajectory, i) for i in range(len(policy_vector))]
    episode_winner = choose_winner(cumulative_reward_vector)
    return episode_winner


def choose_winner(cumulative_reward_vector, break_ties=random.choice):
    indexes_max_score = np.argwhere(cumulative_reward_vector == np.amax(cumulative_reward_vector))
    return break_ties(indexes_max_score.flatten().tolist())


def create_benchmark_process(benchmarking_episodes, createNewEnvironment, benchmark_job, pool, matrix_queue, name):
    """
    Creates a benchmarking process for the precomputed benchmark_job.
    The results of the benchmark will be put in the matrix_queue to populate confusion matrix

    :param benchmarking_episodes: Number of episodes that each benchmarking process will run for
    :param createNewEnvironment: OpenAI gym environment creation function
    :param benchmark_job: precomputed BenchmarkingJob
    :param pool: ProcessPoolExecutor shared between benchmarking_jobs to carry out benchmarking matches
    :param matrix_queue: Queue reference sent to benchmarking process, where it will put the bencharmking result
    :param name: BenchmarkingJob name identifier
    """
    benchmark_process = Process(target=benchmark_match_play_process,
                                args=(benchmarking_episodes, createNewEnvironment,
                                      benchmark_job, pool, matrix_queue, name))
    benchmark_process.start()
    return benchmark_process
