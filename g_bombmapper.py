'''
BombMapper
'''
# import any external packages by un-commenting them
# if you'd like to test / request any additional packages - please check with the Coder One team
import random
import time
import numpy as np
# import pandas as pd
# import sklearn
from .g_utils import *

def in_bomb_range(bomb_pos, tile_pos, power=2):
    return hamming_dist(bomb_pos, tile_pos) <= power

class Bomb:
    def __init__(self, pos, ttl):
        self.update(pos, ttl)
    def update(self, pos, ttl):
        self.pos = pos
        self.ttl = ttl

class BombMapper:
    def __init__(self):
        self.bomb_map = None
        self.bombset = set()
        self.game_tick = 0

    def update(self, game_state):
        self.game_tick = game_state.tick_number
        if self.bomb_map is None:
            self.bomb_map = np.zeros(game_state.size)*np.nan
        for b in game_state.bombs:
            if b not in self.bombset:
                self.bomb_map[b] = game_state.tick_number
        for exp_b in self.bombset.difference(set(game_state.bombs)):
            self.bomb_map[exp_b] = np.nan
        self.bombset = set(game_state.bombs)
        # return self.get_bomb_list(game_state)

    def timeleft(self):
        return 35 - (self.game_tick - self.bomb_map)

    def explosion_map(self, game_state):
        exp_map = np.copy(self.timeleft())
        recompute_bombs = []
        for b in self.bombset:
            for coord, _ in zip(*neighbouring_tiles(b, game_state, steps=2)):
                if coord in self.bombset:
                    recompute_bombs.append(coord)
                    self.bomb_map[coord] = min(self.bomb_map[coord], self.bomb_map[b]+1)
                if np.isnan(exp_map[coord]):
                    exp_map[coord] = self.timeleft()[b]
                else:
                    exp_map[coord] = min(exp_map[coord], self.timeleft()[b])

        for b in recompute_bombs:
            for coord, _ in zip(*neighbouring_tiles(b, game_state, steps=2)):
                if np.isnan(exp_map[coord]):
                    exp_map[coord] = self.timeleft()[b]
                else:
                    exp_map[coord] = min(exp_map[coord], self.timeleft()[b])
        return exp_map

    def neighborhood_bomb(self, pos, game_state, grid_radius=3):
        col, row = game_state.size
        neighborhood = np.zeros((2*grid_radius+1,2*grid_radius+1))*np.nan
        col_start = pos[0] - grid_radius
        col_end = pos[0] + grid_radius
        row_start = pos[1] - grid_radius
        row_end = pos[1] + grid_radius
        bomb_window = self.bomb_map[col_start:col_end+1, row_start:row_end+1]
        # print(35 - (self.game_tick - array_to_str(bomb_window)))
        return 35 - (self.game_tick - bomb_window)

    def get_bomb_list(self, game_state):
        bombs = [Bomb(b, self.timeleft()[b]) for b in game_state.bombs]
        neighbours = [[] for _ in range(len(bombs))]
        for i in range(len(bombs)-1):
            for j in range(i+1,len(bombs)):
                if in_bomb_range(bombs[i].pos, bombs[j].pos):
                    neighbours[i].append(j)
                    neighbours[j].append(i)
        updated = True
        while updated:
            updated = False
            for b in range(len(bombs)):
                for n in neighbours[b]:
                    if bombs[b].ttl > bombs[n].ttl + 1:
                        updated = True
                        bombs[b].ttl = bombs[n].ttl + 1

        sb = np.zeros((len(bombs),2),dtype=int)
        for idx in range(len(bombs)):
            sb[idx,0] = bombs[idx].ttl
            sb[idx,1] = idx
        sb = sb[sb[:,0].argsort()]
        sorted_bombs = [bombs[i] for i in sb[:,1]]
        return sorted_bombs

    def __str__(self):
        return np.rot90(self.timeleft()).__str__()
