'''
Utils
'''
# import any external packages by un-commenting them
# if you'd like to test / request any additional packages - please check with the Coder One team
import random
import time
import numpy as np
# import pandas as pd
# import sklearn


class block_type:
    BOMB = 8
    TREASURE = 7
    AMMO = 6
    SOFT_BLOCKS = 5
    ORE_BLOCKS = 4
    HARD_BLOCKS = 3
    OPPONENT = 2
    PLAYER = 1
block_type_dict = {None: 0, 0:block_type.PLAYER, 1:block_type.OPPONENT, 'ib':block_type.HARD_BLOCKS, 'sb':block_type.SOFT_BLOCKS, 'ob':block_type.ORE_BLOCKS, 'b':block_type.BOMB, 'a':block_type.AMMO, 't':block_type.TREASURE}

def array_to_str(array_to_print):
    return np.rot90(array_to_print)

def hamming_dist(p1, p2):
    if p1 is None or p2 is None:
        return 120
    return np.abs(p1[0]-p2[0])+np.abs(p1[1]-p2[1])

def closest_object(loc, list_of_objects, exceptions=[]):
    dist = 120
    target_pos = None
    for a in list_of_objects:
        if a in exceptions:
            continue
        new_dist = hamming_dist(loc, a)
        if dist > new_dist:
            target_pos = a
            dist = new_dist
    return target_pos

def second_closest_object(loc, list_of_objects, exceptions=[]):
    dist = 120
    second_dist = 120
    target_pos = None
    second_target_pos = None
    for a in list_of_objects:
        if a in exceptions:
            continue
        new_dist = hamming_dist(loc, a)
        if second_dist > new_dist:
            if dist > new_dist:
                second_dist = dist
                dist = new_dist
                second_target_pos = target_pos
                target_pos = a
            else:
                second_dist = new_dist
                second_target_pos = a
    if second_target_pos is None:
        second_target_pos = target_pos
    return second_target_pos


def state_to_array(game_state, player_id, match_gui=False):
    game_map = np.zeros(game_state.size)
    objects = [game_state.bombs, game_state.ammo, game_state.indestructible_blocks, game_state.soft_blocks, game_state.ore_blocks, game_state.treasure]
    keys = [block_type.BOMB, block_type.AMMO, block_type.HARD_BLOCKS, block_type.SOFT_BLOCKS, block_type.ORE_BLOCKS, block_type.TREASURE]
    for obj_list, k in zip(objects, keys):
        for obj in obj_list:
            game_map[obj] = k
    for i, opp in enumerate(game_state.opponents(2)):
        game_map[opp] += block_type.PLAYER if i == player_id else block_type.OPPONENT

    if match_gui:
        game_map = array_to_str(game_map)
    return game_map

def neighborhood_array(game_state, player_loc, grid_radius=3, match_gui=False):
    neighborhood = np.zeros((2*grid_radius+1,2*grid_radius+1))*np.nan
    for i in range(-grid_radius,grid_radius+1):
        for j in range(-grid_radius,grid_radius+1):
            pos = (player_loc[0]+i, player_loc[1]+j)
            if game_state.is_in_bounds(pos):
                obj = game_state.entity_at(pos)
                neighborhood[i+grid_radius,j+grid_radius] = block_type_dict[obj]
    if match_gui:
        neighborhood = array_to_str(neighborhood)
    return neighborhood

def get_valid_actions(game_state, player_state):
    valid_actions = ['']
    game_map = state_to_array(game_state, player_state.id)
    player_loc = player_state.location

    for coord, direction in zip(*neighbouring_tiles(player_loc, game_state)):
        if game_state.entity_at(player_loc) not in ['ib', 'sb', 'ob', 'b', 1-player_state.id]:
            valid_actions.append(direction)
    if player_state.ammo > 0:
        on_bomb = False
        for b in game_state.bombs:
            if b == player_loc:
                on_bomb = True
                break
        if not on_bomb:
            valid_actions.append('p')
    return valid_actions, game_map


def neighbouring_tiles(coord, game_state, board_size=(12,10), steps=1):
    tiles, directions = [], []
    for s in range(1,steps+1):
        for delta, dir in zip([(-s, 0), (s, 0), (0, s), (0,-s)],['l','r','u','d']):
            new_pos = (coord[0]+delta[0],coord[1]+delta[1])
            if game_state.is_in_bounds(new_pos):
                tiles.append(new_pos)
                directions.append(dir)
    return tiles, directions


def check_ore_blocks(game_state, player_loc, pathfinder, blockmap_future):
    easy_ore_available = False
    easy_ore_list = []
    for ob in game_state.ore_blocks:
        n_space4bomb = 0
        n_bombs_around = 0
        tiles, n_whitespace = neighbouring_whitespace(ob, game_state)
        if n_whitespace >= blockmap_future[ob]:
            # n_space4bomb = n_whitespace
            for new_pos in tiles:
                # path, path_found = pathfinder.search(player_loc, new_pos, game_state, 1, occupied_blocktypes=['sb', 'ib', 'ob', 'b'])
                # if path_found:
                n_space4bomb += 1
                    # if game_state.entity_at(new_pos) is 'b':
                    #     n_bombs_around += 1
        # if n_space4bomb >= 3 and n_bombs_around < 3:
        if n_space4bomb >= blockmap_future[ob]:
            easy_ore_list.append(ob)
            easy_ore_available = True
    return easy_ore_available, easy_ore_list



def check_far_ore_blocks(game_state, player_loc, pathfinder, blockmap_future):
    snipe_ore_available = False
    easy_ore_snipepos = []
    easy_ore_list = []
    for ob in game_state.ore_blocks:
        if blockmap_future[ob] == 1:
            for delta in [(-2, 0), (2, 0), (0, 2), (0,-2)]:
                new_pos = (ob[0]+delta[0],ob[1]+delta[1])
                between = (int(ob[0]+delta[0]/2),int(ob[1]+delta[1]/2))
                if game_state.is_in_bounds(new_pos):
                    if game_state.entity_at(new_pos) is None and game_state.entity_at(between) in ['b', 0, 1]:
                        easy_ore_snipepos.append(new_pos)
                        easy_ore_list.append(ob)
                        snipe_ore_available = True
    return easy_ore_snipepos, easy_ore_list, snipe_ore_available


def check_ore_blocks_legacy(game_state):
    easy_ore_available = False
    easy_ore_list = []
    for ob in game_state.ore_blocks:
        n_space4bomb = 0
        n_bombs_around = 0
        for delta in [(-1, 0), (1, 0), (0, 1), (0,-1)]:
            new_pos = (ob[0]+delta[0],ob[1]+delta[1])
            if game_state.is_in_bounds(new_pos):
                if game_state.entity_at(new_pos) is None or game_state.entity_at(new_pos) is 'b':
                    n_space4bomb += 1
                    if game_state.entity_at(new_pos) is 'b':
                        n_bombs_around += 1
        if n_space4bomb >= 3 and n_bombs_around < 3:
            easy_ore_list.append(ob)
            easy_ore_available = True
    return easy_ore_available, easy_ore_list



def neighbouring_whitespace(coord, game_state, board_size=(12,10), steps=1, visited=[]):
    tiles, directions = [], []
    n_whitespace = 0
    for s in range(1,steps+1):
        for delta in [(-s, 0), (s, 0), (0, s), (0,-s)]:
            new_pos = (coord[0]+delta[0],coord[1]+delta[1])
            if game_state.is_in_bounds(new_pos) and new_pos not in visited:
                tiles.append(new_pos)
                if game_state.entity_at(new_pos) is None:
                    n_whitespace += 1
    return tiles, n_whitespace


def neighbor_tile_values(game_state, player_loc, opp_id, game_map, exp_map):
    values = [-10000 for _ in range(5)]
    for i, delta in enumerate([(-1,0), (1,0), (0, 1), (0, -1), (0,0)]):
    # for i, delta in enumerate([(1,0), (0,-1), (0,1), (-1,0), (0,0)]):
        new_pos = (player_loc[0]+delta[0], player_loc[1]+delta[1])
        if game_state.is_in_bounds(new_pos) and game_state.entity_at(new_pos) not in ['sb', 'ob', 'ib', 'b', opp_id]:
            values[i] = 5000
            neighbor, n_whitespace = neighbouring_whitespace(new_pos, game_state)
            if n_whitespace == 0:
                values[i] -= 5000
            values[i] += 20*n_whitespace
            for n in neighbor:
                neighbor2, nn_whitespace = neighbouring_whitespace(n, game_state, [new_pos, n])
                values[i] += 20*nn_whitespace
                if nn_whitespace == 0:
                    values[i] -= 1000
                for n2 in neighbor2:
                    _, nnn_whitespace = neighbouring_whitespace(n2, game_state)
                    values[i] += 5*nnn_whitespace
        if delta == (0,0) and not np.isnan(exp_map[new_pos]):
            values[i] -= 100*(35-exp_map[new_pos])
        if delta == (0,0) and np.isnan(exp_map[new_pos]):
            values[i] += 5000
        for b in game_state.bombs:
            if (np.abs(b[0]-new_pos[0])<=2 and np.abs(b[1]-new_pos[1])==0) or (np.abs(b[1]-new_pos[1])<=2 and np.abs(b[0]-new_pos[0])==0):
                values[i] -= 10*(50 - min(3, exp_map[new_pos] if game_state.is_in_bounds(new_pos) else 0))
    return values
