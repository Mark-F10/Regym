import os
import sys
sys.path.append(os.path.abspath('../../'))
import pytest

import torch

from test_fixtures import ppo_config_dict, RPSenv, RPSTask

from rl_algorithms.agents import build_PPO_Agent
from rl_algorithms.PPO import PPOAlgorithm
from rl_algorithms import rockAgent
from multiagent_loops import simultaneous_action_rl_loop

from unittest.mock import Mock


def test_ppo_can_take_actions(RPSenv, RPSTask, ppo_config_dict):
    agent = build_PPO_Agent(RPSTask, ppo_config_dict)
    number_of_actions = 30
    for i in range(number_of_actions):
        # asumming that first observation corresponds to observation space of this agent
        random_observation = RPSenv.observation_space.sample()[0]
        a = agent.take_action(random_observation)
        observation, rewards, done, info = RPSenv.step([a, a])
        # TODO technical debt
        # assert RPSenv.observation_space.contains([a, a])
        # assert RPSenv.action_space.contains([a, a])


def test_learns_to_beat_rock_in_RPS(RPSTask, ppo_config_dict):
    '''
    Test used to make sure that agent is 'learning' by learning a best response
    against an agent that only plays rock in rock paper scissors.
    i.e from random, learns to play only (or mostly) paper
    '''
    from rps_test import learns_against_fixed_opponent_RPS

    agent = build_PPO_Agent(RPSTask, ppo_config_dict)
    assert agent.training
    learns_against_fixed_opponent_RPS(agent, fixed_opponent=rockAgent,
                                      training_episodes=1000, inference_percentage=0.9,
                                      reward_threshold=0.1)
