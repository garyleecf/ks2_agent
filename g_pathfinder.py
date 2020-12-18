'''
ASTAR
'''
# import any external packages by un-commenting them
# if you'd like to test / request any additional packages - please check with the Coder One team
import random
import time
import numpy as np
# import pandas as pd
# import sklearn
_MAX_ATTEMPT = 1000
from .g_utils import neighbouring_whitespace

class Node:
    def __init__(self, pos, parent=None):
        self.pos = pos
        self.parent = parent
        self.f = 0
        self.g = 0
        self.h = 0
    def __eq__(self, other):
        return self.pos == other.pos

class PathFinding:
    def __init__(self):
        self.reset()

    def reset(self):
        self.to_visit = []
        self.visited = []

    def path(self, curr_node):
        path = []
        action = []
        curr = curr_node
        while curr is not None:
            path.append(curr.pos)
            curr = curr.parent
        path = path[::-1]
        return path

    def search(self, start, end, game_state, cost=1, occupied_blocktypes=['sb', 'ib', 'ob', 'b']):
        start_node = Node(start)
        start_node.f, start_node.g, start_node.h = 0, 0, 0
        end_node = Node(end)
        end_node.f, end_node.g, end_node.h = 0, 0, 0

        self.reset()
        self.to_visit.append(start_node)

        attempt = 0
        while self.to_visit:
            attempt += 1
            curr_node = self.to_visit[0]
            curr_idx = 0
            for i, node in enumerate(self.to_visit):
                if node.f < curr_node.f:
                    curr_node = node
                    curr_idx = i
            if attempt > _MAX_ATTEMPT:
                return self.path(curr_node), False

            self.to_visit.pop(curr_idx)
            self.visited.append(curr_node)
            # print([n.pos for n in self.visited])

            if curr_node == end_node:
                return self.path(curr_node), True

            neighbor = []
            for delta in [(1,0), (0,-1), (0,1), (-1,0)]:
                new_pos = (curr_node.pos[0] + delta[0], curr_node.pos[1] + delta[1])
                if not game_state.is_in_bounds(new_pos) or game_state.entity_at(new_pos) in occupied_blocktypes:
                    if new_pos != end:
                        continue
                # Create new node
                new_node = Node(new_pos, curr_node)
                neighbor.append(new_node)
            for node in neighbor:
                if node in self.visited:
                    continue
                node.g = curr_node.g + cost
                node.h = (((node.pos[0] - curr_node.pos[0]) ** 2) + ((node.pos[1] - curr_node.pos[1]) ** 2)) + pseudo_value(node.pos, game_state)
                node.f = node.g + node.h
                if [n for n in self.to_visit if n==node and n.g <= node.g]:
                    continue
                self.to_visit.append(node)
        return None, False

def pseudo_value(new_pos, game_state):
    value = 0
    neighbor, n_whitespace = neighbouring_whitespace(new_pos, game_state)
    value += 0.1*n_whitespace
    for n in neighbor:
        neighbor2, nn_whitespace = neighbouring_whitespace(n, game_state, [new_pos, n])
        for n2 in neighbor2:
            _, nnn_whitespace = neighbouring_whitespace(n2, game_state)
            value += 0.05*nnn_whitespace
    return value
