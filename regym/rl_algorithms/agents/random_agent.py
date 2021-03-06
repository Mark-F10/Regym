from typing import List
import random

import gym

from regym.environments import EnvType
from regym.rl_algorithms.agents import Agent


class RandomAgent(Agent):
    '''
    Mostly useful for debugging purposes.

    Agent that behaves randomly in an environment by sampling random actions
    from the environment's underlying action space. It will never sample an invalid
    action if a list of legal actions is provided.
    '''

    def __init__(self, name: str, action_space: gym.spaces.Space):
        super(RandomAgent, self).__init__(name, requires_environment_model=False)
        self.action_space = action_space

    def take_action(self, state_or_environment, legal_actions: List[int] = None):
        if legal_actions is not None: action = random.choice(legal_actions)
        else: action = self.action_space.sample()
        return action

    def handle_experience(self, s, a, r, succ_s, done=False):
        super(RandomAgent, self).handle_experience(s, a, r, succ_s, done)

    def clone(self):
        return RandomAgent(name=self.name, action_space=self.action_space)


    def __repr__(self):
        return f'{self.name}. Action space: {self.action_space}'


def build_Random_Agent(task, config, agent_name: str):
    '''
    Builds an agent that is able to randomly act in a task

    :param task: Task in which the agent will be able to act
    :param config: Ignored, left here to keep `build_X_Agent` interface consistent
    :param name: String identifier
    '''
    if task.env_type == EnvType.SINGLE_AGENT: action_space = task.env.action_space
    # Assumes all agents share same action space
    else: action_space = task.env.action_space.spaces[0]
    return RandomAgent(name=agent_name, action_space=action_space)
