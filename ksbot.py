'''
ks Bot
'''

# import any external packages by un-commenting them
# if you'd like to test / request any additional packages - please check with the Coder One team
import random
import time
# import numpy as np
# import pandas as pd
# import sklearn
from .g_utils import *
from .g_pathfinder import *
from .g_bombmapper import *
from .g_blockmapper import *

_DEBUG_PRINT = False

_DETAILED_DEBUG_PRINT = False

class Agent:
    ACTION_PALLET = ['', 'u','d','l','r','p', '']

    def __init__(self):
        self.name = "glee"
        """ Initialization
        """
        self.player_id = None
        self.opp_id = None
        self.i = -1

        self.bombmapper = BombMapper()
        self.blockmapper = BlockMapper()
        self.pathfinder = PathFinding()

        self.path_plan = None
        self.bored = True
        self.plan_to_bomb = False
        self.post_bombing = False
        self.ks_mode = False

        self.opp_prev_loc = None
        self.opp_idle = 0

        self.current_target = None
        self.put_bomb_on_target = False

        self.current_mode = None
        self.last_mode = None
        self.sb_bombed = []
        self.danger_past = 0
        self.huntdown_opp = False

        self.unreachables = []
        self.my_bombs = []

        self.printed_hunter = False

    def next_move(self, game_state, player_state):
        if (game_state.tick_number - self.i) <= 0:
            return ''
        if _DETAILED_DEBUG_PRINT:
            print("--")
            print(f"Position: {player_state.location}, Opp Position: {game_state.opponents(2)[1-player_state.id]}")
            print(f"Current Mode: {self.last_mode if self.current_mode is None else self.current_mode}")
            if self.current_mode is not None:
                self.last_mode = self.current_mode
            print(f"Current Target: {self.current_target}")
            print(f"Bored: {self.bored}, Plan2Bomb: {self.plan_to_bomb}, KS Mode: {self.ks_mode}, PostBomb: {self.post_bombing}")
            print(f"Path: {self.path_plan}")
            print(f"Danger Past: {self.danger_past}")
            print("--")

        if self.current_mode:
            if _DEBUG_PRINT:
                if not (self.printed_hunter and self.current_mode == "Hunter"):
                    print(self.current_mode)
            self.printed_hunter = self.current_mode == "Hunter"
            self.current_mode = None

        """
        This method is called each time the agent is required to choose an action
        """
        if self.player_id is None:
            self.player_id = player_state.id
        player_loc = player_state.location
        opp_loc = game_state.opponents(2)[1-self.player_id]
        if self.opp_prev_loc is None:
            self.opp_prev_loc = opp_loc

        if (game_state.tick_number - self.i) != 1:
            # if _DEBUG_PRINT:
            print(f'Tick {game_state.tick_number}: {game_state.tick_number-self.i}')
        self.i = game_state.tick_number


        self.bombmapper.update(game_state)
        self.blockmapper.update(game_state)
        valid_actions, game_map = get_valid_actions(game_state,player_state)

        if self.bored:
            self.put_bomb_on_target = False
        ####################
        # Danger Check and Evasion Maneuveur:
        ####################
        # On the safe side: avoid blast radius for 3 ticks
        self.danger_past -= 1
        in_danger = self.danger_past > 0
        for b in game_state.bombs:
            if hamming_dist(player_loc, b)<=3 or (np.abs(b[0]-player_loc[0])<=3 and np.abs(b[1]-player_loc[1])==0) or (np.abs(b[1]-player_loc[1])<=3 and np.abs(b[0]-player_loc[0])==0):
                if self.bombmapper.explosion_map(game_state)[b] < 5:
                    in_danger = True
                    self.danger_past = 2
                    break
        if (in_danger or self.post_bombing):
            self.current_mode = 'Evading' if in_danger else 'AfterBomb'
            # Ditch whatever plan
            self.path_plan = []
            self.bored = True
            self.post_bombing = False

            exp_map = self.bombmapper.explosion_map(game_state)
            value = neighbor_tile_values(game_state, player_loc, 1-self.player_id, game_map, exp_map)
            # if _DEBUG_PRINT:
            #     print(value)
            movement_options = ['l','r','u','d', '']
            action_id = random.choice([i for i, v in enumerate(value) if v==np.nanmax(value)])
            return movement_options[action_id]

        ####################
        # Exploit KS-ing:
        ####################
        for b in self.my_bombs:
            if game_state.entity_at(b) is not 'b':
                self.my_bombs.remove(b)

        if self.bored and player_state.ammo > 0:
            candidate_target_pos = []
            self.ks_mode = False
            for bomb in game_state.bombs:
                if bomb in self.my_bombs:
                    continue
                neighborhood, _ = neighbouring_tiles(bomb, game_state, steps=2)
                for block in neighborhood:
                    if self.blockmapper.blockmap_future[block] > 1:
                        continue
                    if game_state.entity_at(block) in ['ob']:
                        target_pos = None
                        if hamming_dist(bomb,block) == 2:
                            if np.abs(bomb[0] - block[0]) == 2:
                                target_pos = (int(bomb[0]+block[0])/2, bomb[1])
                            elif np.abs(bomb[1] - block[1]) == 2:
                                target_pos = (bomb[0], int(bomb[1]+block[1])/2)
                        if target_pos is not None and game_state.entity_at(target_pos) is None:
                            candidate_target_pos.append(target_pos)
                    if game_state.entity_at(block) in ['sb']:
                        target_pos = None
                        if hamming_dist(bomb,block) == 2:
                            if np.abs(bomb[0] - block[0]) == 2:
                                target_pos = (int(bomb[0]+block[0])/2, bomb[1])
                            elif np.abs(bomb[1] - block[1]) == 2:
                                target_pos = (bomb[0], int(bomb[1]+block[1])/2)
                        if target_pos is not None and game_state.entity_at(target_pos) is None:
                            candidate_target_pos.append(target_pos)
            unreachables = []
            i = 0
            while len(unreachables) < len(candidate_target_pos):
                # target_pos = closest_object(player_loc, candidate_target_pos, unreachables)
                target_pos = candidate_target_pos[i]
                i += 1
                path, path_found = self.pathfinder.search(player_loc, target_pos, game_state, 1, occupied_blocktypes=['sb', 'ib', 'ob', 'b', 1-self.player_id])
                if path_found:
                    self.path_plan = path
                    self.bored = False
                    self.current_target = target_pos
                    self.current_mode = 'KS Time'
                    self.ks_mode = True
                    break
                else:
                    unreachables.append(target_pos)

        ####################
        # Exploit Idling Opponent:
        ####################
        # If opponent has been idle, plant bombs beside
        if hamming_dist(opp_loc, self.opp_prev_loc)==0:
            self.opp_idle += 1
            if self.opp_idle >= 3 and hamming_dist(player_loc, opp_loc)==1:
                self.current_mode = 'Exploit Idling'
                if player_state.ammo:
                    self.post_bombing = True
                    self.my_bombs.append(player_loc)
                    return 'b'
                else:
                    self.huntdown_opp = False
                    self.bored = True
                    self.post_bombing = False
        else:
            self.opp_prev_loc = opp_loc
            self.opp_idle = 0


        if np.nansum(self.blockmapper.blockmap) == 0:
            if hamming_dist(player_loc, opp_loc)<=2:
                self.current_mode = 'Crazy Bominggg'
                if player_state.ammo:
                    self.post_bombing = True
                    self.my_bombs.append(player_loc)
                    return 'b'
                else:
                    self.huntdown_opp = False
                    self.bored = True
                    self.post_bombing = False
            else:
                self.huntdown_opp = True


        ####################
        # Find next plan:
        ####################
        # Find Ammo or Treasure (prioritise ammo)
        new_target_pos = closest_object(player_loc, game_state.ammo+game_state.treasure)
        # if new_target_pos is None:
        #     self.unreachables = []
        # if len(self.unreachables) >= len(game_state.ammo + game_state.treasure):
        #     self.unreachables = []
        is_gone = False
        if self.current_target is not None:
            is_gone = not (game_state.entity_at(self.current_target) == 'a' or game_state.entity_at(self.current_target) == 't')
        # if _DEBUG_PRINT:
        #     print(f"Finding Ammo/Treasure: {(game_state.ammo or game_state.treasure)}, {(self.bored or is_gone or hamming_dist(new_target_pos, player_loc) < hamming_dist(self.current_target, player_loc))}, {not self.ks_mode}")
        closer_new_target = False
        # if hamming_dist(new_target_pos, player_loc) < hamming_dist(self.current_target, player_loc):
        #     path, path_found = self.pathfinder.search(player_loc, target_pos, game_state, 1, occupied_blocktypes=['sb', 'ib', 'ob', 'b'])
        #     closer_new_target = path_found

        if (game_state.ammo + game_state.treasure) and (self.bored or is_gone or closer_new_target) and not self.ks_mode:
            unreachables = []
            while len(unreachables) < len((game_state.ammo + game_state.treasure)):
                target_pos = closest_object(player_loc, []+game_state.ammo+game_state.treasure, unreachables)
                if hamming_dist(player_loc, opp_loc) <= 2 and hamming_dist(player_loc, target_pos)>1 and hamming_dist(player_loc, target_pos)<=hamming_dist(opp_loc, target_pos):
                    target_pos = second_closest_object(player_loc, game_state.ammo+game_state.treasure, unreachables)
                    if _DEBUG_PRINT:
                        print(f"Changing priority: {target_pos}")
                # problem: closest object may not be reachable
                path, path_found = self.pathfinder.search(player_loc, target_pos, game_state, 1, occupied_blocktypes=['sb', 'ib', 'ob', 'b'])
                if path_found:
                    self.path_plan = path
                    self.bored = False
                    self.current_target = target_pos
                    self.current_mode = f'Ammo/Treasure Hunting: {target_pos}'
                    break
                else:
                    unreachables.append(target_pos)
            if _DEBUG_PRINT:
                print(f"Can't reach ammo/treasures: {unreachables}")

        easy_ore_available, easy_ore_list = check_ore_blocks(game_state, player_loc, self.pathfinder, self.blockmapper.blockmap_future)
        if self.bored and easy_ore_available:# and player_state.reward > 7:
            if easy_ore_list and self.bored and player_state.ammo > 0:
                if _DEBUG_PRINT:
                    print(f"Easy Ore: {easy_ore_available}, {[(ob, self.blockmapper.blockmap_future[ob]) for ob in easy_ore_list if self.blockmapper.blockmap_future[ob] <= player_state.ammo and self.blockmapper.blockmap_future[ob] > 0 and (self.blockmapper.blockmap_future[ob] < 3 or (self.blockmapper.blockmap_future[ob] == 3 and player_state.reward > 7))]}")
                # print(np.rot90(blockmap_future))
                for easy_ob in easy_ore_list:
                    if self.blockmapper.blockmap_future[easy_ob] <= player_state.ammo and self.blockmapper.blockmap_future[easy_ob] > 0 and (self.blockmapper.blockmap_future[easy_ob] < 3 or (self.blockmapper.blockmap_future[easy_ob] == 3 and player_state.reward > 7)):
                        target_pos = easy_ob
                        # if hamming_dist(target_pos, player_loc) > 1:
                        path, path_found = self.pathfinder.search(player_loc, target_pos, game_state, 1, occupied_blocktypes=['sb', 'ib', 'ob', 'b'])
                        if path_found:
                            self.path_plan = path
                            self.bored = False
                            self.plan_to_bomb = True
                            self.current_target = target_pos
                            self.current_mode = 'Easy Ore Block Bombing'
                            break
        easy_ore_snipepos, easy_ore_list, snipe_ore_available = check_far_ore_blocks(game_state, player_loc, self.pathfinder, self.blockmapper.blockmap_future)
        if self.bored and snipe_ore_available:# and player_state.reward > 7:\
            if easy_ore_snipepos and self.bored and player_state.ammo > 0:
                if _DEBUG_PRINT:
                    print(f"Snipe Ore: {snipe_ore_available}, {easy_ore_snipepos}, {[(ob, self.blockmapper.blockmap_future[ob]) for ob in easy_ore_list if self.blockmapper.blockmap_future[ob] <= player_state.ammo and self.blockmapper.blockmap_future[ob] > 0 and (self.blockmapper.blockmap_future[ob] < 3 or (self.blockmapper.blockmap_future[ob] == 3 and player_state.reward > 7))]}")
                for target_pos, easy_ob in zip(easy_ore_snipepos, easy_ore_list):
                    if self.blockmapper.blockmap_future[easy_ob] > 0:
                        path, path_found = self.pathfinder.search(player_loc, target_pos, game_state, 1, occupied_blocktypes=['sb', 'ib', 'ob', 'b'])
                        if path_found:
                            self.path_plan = path
                            self.bored = False
                            self.plan_to_bomb = True
                            self.current_target = target_pos
                            self.current_mode = 'Snipe Ore Block Bombing'
                            self.put_bomb_on_target = True
                            break

        if game_state.soft_blocks and self.bored and player_state.ammo > 0:
            # target_pos = closest_object(player_loc, game_state.soft_blocks, self.sb_bombed)
            target_pos = closest_object(player_loc, self.blockmapper.untargeted_soft_blocks)
            checked = [target_pos]
            path_found = False
            while len(checked) < len(game_state.soft_blocks):
                if hamming_dist(target_pos, player_loc) > 1:
                    path, path_found = self.pathfinder.search(player_loc, target_pos, game_state, 1, occupied_blocktypes=['sb', 'ib', 'ob', 'b'])
                    if path_found:
                        self.path_plan = path
                        self.bored = False
                        self.plan_to_bomb = True
                        self.current_target = target_pos
                        self.current_mode = 'Soft Block Bombing'
                        break
                target_pos = closest_object(player_loc, self.blockmapper.untargeted_soft_blocks, checked)
                checked.append(target_pos)

        if game_state.ore_blocks and self.bored and player_state.ammo > 0:
            # target_pos = closest_object(player_loc, game_state.ore_blocks)
            target_pos = closest_object(player_loc, self.blockmapper.untargeted_ore_blocks)
            if hamming_dist(target_pos, player_loc) > 1:
                path, path_found = self.pathfinder.search(player_loc, target_pos, game_state, 1, occupied_blocktypes=['sb', 'ib', 'ob', 'b'])
                if path_found:
                    self.path_plan = path
                    self.bored = False
                    self.plan_to_bomb = True
                    self.current_target = target_pos
                    self.current_mode = 'Ore Block Bombing'


        if self.bored or self.huntdown_opp:
            path, path_found = self.pathfinder.search(player_loc, opp_loc, game_state, 1)
            if path_found:
                self.path_plan = path
                self.current_target = opp_loc
                self.current_mode = 'Hunter'
            self.huntdown_opp = False
            self.bored = True
            self.post_bombing = False
            self.ks_mode = False


        ####################
        # Follow that plan:
        ####################
        if _DETAILED_DEBUG_PRINT:
            print(f"Updated Target: {self.current_target}")
            print(f"Path: {self.path_plan}")
        # If there is a plan, follow that plan
        if self.path_plan:
            has_moved = False
            if self.path_plan[0] == player_loc:
                self.path_plan.pop(0)
                has_moved = True
                if self.put_bomb_on_target and len(self.path_plan)==0:
                    self.put_bomb_on_target = False
                    self.current_mode = 'Boom'
                    path_action = 'b'
                    self.post_bombing = True
                    self.plan_to_bomb = False
                    self.my_bombs.append(player_loc)
                    return path_action

                if self.current_target is not None:
                    if (game_state.entity_at(self.current_target) is None and not self.put_bomb_on_target) or game_state.entity_at(self.current_target) is 'b':
                        if self.current_target != opp_loc:
                            self.current_mode = 'Item snatched'
                        self.ks_mode = False
                        self.bored = True
                        self.post_bombing = False
                        self.plan_to_bomb = False
                        self.path_plan = []
                        self.current_target = None

                if self.ks_mode and len(self.path_plan)==0:
                    self.current_mode = 'KS-ed'
                    self.ks_mode = False
                    self.bored = True
                    path_action = 'b'
                    self.post_bombing = True
                    self.plan_to_bomb = False
                    neighbors, _ = neighbouring_tiles(player_loc, game_state)
                    for nn in neighbors:
                        if game_state.entity_at(nn) == 'sb':
                            self.sb_bombed.append(nn)
                    self.my_bombs.append(player_loc)
                    return path_action
                if self.ks_mode and game_state.entity_at(self.current_target) is 'b':
                    self.current_mode = 'Cannot KS'
                    self.ks_mode = False
                    self.bored = True
                    self.path_plan = []

            if self.path_plan:
                next_pos = self.path_plan[0]
                path_action = ''
                if game_state.entity_at(next_pos) in ['sb', 'ob']:
                    if self.plan_to_bomb:
                        self.current_mode = 'Boom'
                        path_action = 'b' #if self.blockmapper.blockmap_future[next_pos] > 0 else ''
                        self.post_bombing = True
                        self.plan_to_bomb = False
                        if game_state.entity_at(next_pos) == 'sb':
                            self.sb_bombed.append(next_pos)
                        self.my_bombs.append(player_loc)
                        return path_action
                elif game_state.entity_at(next_pos) in ['b']:
                    self.path_plan = []
                else: # Movement
                    if next_pos[0] - player_loc[0] == 0:
                        if next_pos[1] > player_loc[1]:
                            path_action = 'u'
                        if next_pos[1] < player_loc[1]:
                            path_action = 'd'
                    else:
                        if next_pos[0] > player_loc[0]:
                            path_action = 'r'
                        if next_pos[0] < player_loc[0]:
                            path_action = 'l'
                    if _DETAILED_DEBUG_PRINT:
                        print(path_action)
                    return path_action


        # No more moves left in plan
        if (not self.path_plan) or (game_state.entity_at(self.path_plan[0]) in ['ib', 'sb', 'ob', 'b', 1-self.player_id] and game_state.entity_at(player_loc) == 'b'):
            self.current_mode = f'Nothing to do: {self.current_mode}'
            self.bored = True

            next_action = ''
            path, path_found = self.pathfinder.search(player_loc, opp_loc, game_state, 1)
            if path_found:
                self.path_plan = path
                self.current_target = opp_loc
                self.huntdown_opp = True

            exp_map = self.bombmapper.explosion_map(game_state)
            value = neighbor_tile_values(game_state, player_loc, 1-self.player_id, game_map, exp_map)

            movement_options = ['l','r','u','d', '']
            action_id = random.choice([i for i, v in enumerate(value) if v==np.nanmax(value)])
            next_action = movement_options[action_id]

            return next_action


        # player_loc = player_loc
        # map_array
        # self.bombmapper.timeleft()

        #  # Lets pretend that agent is doing some thinking
        # # time.sleep(1)
        # print(array_to_str(self.bombmapper.neighborhood_bomb(player_loc, game_state, grid_radius=2)))
        # self.bombmapper.neighborhood_bomb(player_loc, game_state, grid_radius=2)

        # #
        # print(neighborhood_array(game_state, player_loc, grid_radius=2, match_gui=True))
        self.current_mode = 'End of Loop'
        return ''#'p' if self.i%2 else 'u'
