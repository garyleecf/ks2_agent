'''
BlockMapper
'''
# import any external packages by un-commenting them
# if you'd like to test / request any additional packages - please check with the Coder One team
import random
import time
import numpy as np
# import pandas as pd
# import sklearn
from .g_utils import hamming_dist

SB_INIT_HP = 1
ORE_INIT_HP = 3

class BlockMapper:
    def __init__(self):
        self.blockmap = None
        self.blockmap_future = None
        self.running_bombset = set()
        self.untargeted_soft_blocks = []
        self.untargeted_ore_blocks = []

    def update(self, game_state):
        if self.blockmap is None:
            self.blockmap = np.zeros(game_state.size,dtype=np.int8)*np.nan
            for o in game_state.ore_blocks:
                self.blockmap[o] = ORE_INIT_HP
            for sb in game_state.soft_blocks:
                self.blockmap[sb] = SB_INIT_HP

        for boom in self.running_bombset.difference(set(game_state.bombs)):
            for o in (game_state.ore_blocks + game_state.soft_blocks):
                if hamming_dist(boom, o) == 1:
                    self.blockmap[o] -= 1
                if hamming_dist(boom, o) == 2:
                    if (np.abs(boom[0] - o[0]) == 2):
                        if game_state.entity_at(((boom[0]+o[0])/2, boom[1])) not in ['ob', 'sb', 'ib', 'b']:
                            self.blockmap[o] -= 1
                    elif (np.abs(boom[1] - o[1]) == 2):
                        if game_state.entity_at((boom[0], (boom[1]+o[1])/2)) not in ['ob', 'sb', 'ib', 'b']:
                            self.blockmap[o] -= 1

        self.blockmap_future = np.copy(self.blockmap)
        for boom in game_state.bombs:
            for o in (game_state.ore_blocks + game_state.soft_blocks):
                if hamming_dist(boom, o) == 1:
                    self.blockmap_future[o] -= 1
                if hamming_dist(boom, o) == 2:
                    if (np.abs(boom[0] - o[0]) == 2):
                        if game_state.entity_at(((boom[0]+o[0])/2, boom[1])) not in ['ob', 'sb', 'ib', 'b']:
                            self.blockmap_future[o] -= 1
                    elif (np.abs(boom[1] - o[1]) == 2):
                        if game_state.entity_at((boom[0], (boom[1]+o[1])/2)) not in ['ob', 'sb', 'ib', 'b']:
                            self.blockmap_future[o] -= 1

        self.blockmap_future = np.maximum(self.blockmap_future, 0)

        self.untargeted_ore_blocks = []
        for o in game_state.ore_blocks:
            if self.blockmap_future[o] > 0:
                self.untargeted_ore_blocks.append(o)

        self.untargeted_soft_blocks = []
        for o in game_state.soft_blocks:
            if self.blockmap_future[o] > 0:
                self.untargeted_soft_blocks.append(o)


        self.running_bombset = set(game_state.bombs)

    def ore_hp_left(self):
        return self.blockmap

    def __str__(self):
        return np.rot90(self.blockmap).__str__()
