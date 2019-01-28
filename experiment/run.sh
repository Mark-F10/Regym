#python run.py --environment RockPaperScissors-v0 --experiment_id TESTTQL --number_of_runs 2 --checkpoint_at_iterations 2,8 --benchmarking_episodes 10 --self_play_training_schemes naiveselfplay --algorithms tabularqlearning --fixed_agents rockAgent
python run.py --environment RockPaperScissors-v0 --experiment_id TESTDQN --number_of_runs 2 --checkpoint_at_iterations 2,8 --benchmarking_episodes 10 --self_play_training_schemes naiveselfplay --algorithms deepqlearning --fixed_agents rockAgent
#python run.py --environment RockPaperScissors-v0 --experiment_id TESTDQN --number_of_runs 2 --checkpoint_at_iterations 10,20,30,40,50,60,70,80,90,100 --benchmarking_episodes 10 --self_play_training_schemes naiveselfplay --algorithms deepqlearning --fixed_agents rockAgent
#python run.py --environment RockPaperScissors-v0 --experiment_id TESTDQN --number_of_runs 1 --checkpoint_at_iterations 1,2,3,4,5,6 --benchmarking_episodes 10 --self_play_training_schemes naiveselfplay --algorithms deepqlearning --fixed_agents rockAgent
