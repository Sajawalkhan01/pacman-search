# search.py
# ---------


"""
In search.py, you will implement generic search algorithms which are called by
Pacman agents (in searchAgents.py).
"""

import util
import os
import sys
import csv
import time
import heapq

class SearchProblem:
    """
    This class outlines the structure of a search problem, but doesn't implement
    any of the methods (in object-oriented terminology: an abstract class).

    You do not need to change anything in this class, ever.
    """

    def getStartState(self):
        """
        Returns the start state for the search problem.
        """
        util.raiseNotDefined()

    def isGoalState(self, state):
        """
          state: Search state

        Returns True if and only if the state is a valid goal state.
        """
        util.raiseNotDefined()

    def getSuccessors(self, state):
        """
          state: Search state

        For a given state, this should return a list of triples, (successor,
        action, stepCost), where 'successor' is a successor to the current
        state, 'action' is the action required to get there, and 'stepCost' is
        the incremental cost of expanding to that successor.
        """
        util.raiseNotDefined()

    def getCostOfActions(self, actions):
        """
         actions: A list of actions to take

        This method returns the total cost of a particular sequence of actions.
        The sequence must be composed of legal moves.
        """
        util.raiseNotDefined()


def tinyMazeSearch(problem):
    """
    Returns a sequence of moves that solves tinyMaze.  For any other maze, the
    sequence of moves will be incorrect, so only use this for tinyMaze.
    """
    from game import Directions
    s = Directions.SOUTH
    w = Directions.WEST
    return  [s, s, w, s, w, w, s, w]

#####################################################
#        CSV trace logging (evidence/ folder)       #
#####################################################

EVIDENCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'evidence')
CSV_COLUMNS = ['iteration', 'expanded_state', 'parent', 'action', 'generated_successors',
               'frontier_before', 'frontier_after', 'explored', 'g', 'h', 'f']
MAX_LISTED = 30   # frontier / explored lists longer than this are cut short in the log

# Open log files, one per (layout, algorithm, problem type) in a single run of the
# program. Agents that call a search many times (ClosestDotSearchAgent, the
# autograder) keep appending to the same file instead of creating hundreds of them.
openLogs = {}

def layoutName():
    """Name of the layout given with -l / --layout, or the script name (e.g. autograder)."""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ('-l', '--layout') and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith('--layout='):
            return arg.split('=', 1)[1]
    return os.path.splitext(os.path.basename(sys.argv[0]))[0] or 'run'

def formatState(state):
    """Short text for a state. A FoodSearchProblem state holds a whole food Grid,
    so for those only Pacman's position and the number of dots left are written."""
    if isinstance(state, tuple) and len(state) == 2 and hasattr(state[1], 'asList'):
        return '%s|food_left=%d' % (state[0], state[1].count())
    return str(state)

def formatNumber(x):
    return '%g' % x

def formatList(texts, total, cutAtStart=False):
    """'count: [a, b, ...]' -- the '...' shows that some entries were left out."""
    body = ', '.join(texts)
    if total > len(texts):
        body = '..., ' + body if cutAtStart else body + ', ...'
    return '%d: [%s]' % (total, body)

def frontierSnapshot(frontier, getState=lambda item: item):
    """The frontier as text, listed in the order its entries would be popped.
    For a priority queue each state is shown with its priority as state@priority."""
    if isinstance(frontier, util.PriorityQueue):
        entries = heapq.nsmallest(MAX_LISTED, frontier.heap)
        texts = ['%s@%s' % (formatState(getState(item)), formatNumber(p)) for p, _, item in entries]
        return formatList(texts, len(frontier.heap))
    # util.Stack and util.Queue both pop from the end of their list
    items = frontier.list[-1:-MAX_LISTED - 1:-1]
    return formatList([formatState(getState(item)) for item in items], len(frontier.list))

class TraceLogger:
    """Writes one CSV row for every node a search algorithm takes off the frontier."""

    def __init__(self, algorithm, problem):
        layout = layoutName()
        problemType = type(problem).__name__
        key = (layout, algorithm, problemType)
        if key not in openLogs:
            os.makedirs(EVIDENCE_DIR, exist_ok=True)
            fileName = '%s_%s_%s_%s.csv' % (layout, algorithm, problemType, time.strftime('%Y%m%d_%H%M%S'))
            logFile = open(os.path.join(EVIDENCE_DIR, fileName), 'w', newline='')
            writer = csv.writer(logFile)
            writer.writerow(CSV_COLUMNS)
            openLogs[key] = (logFile, writer)
        self.file, self.writer = openLogs[key]
        self.iteration = 0
        self.expanded = []    # states in the order they were expanded

    def log(self, state, parent, action, successors, frontierBefore, frontierAfter, g, h, f):
        """successors is either the list returned by getSuccessors, or the text
        'GOAL' when the popped state passed the goal test (it is not expanded)."""
        self.iteration += 1
        if successors == 'GOAL':
            generated = 'GOAL (not expanded)'
        else:
            self.expanded.append(state)
            generated = '; '.join('%s %s c=%s' % (formatState(s), a, formatNumber(c))
                                  for s, a, c in successors)
        recent = [formatState(s) for s in self.expanded[-MAX_LISTED:]]
        self.writer.writerow([self.iteration, formatState(state),
                              formatState(parent) if parent is not None else '-',
                              action if action is not None else '-',
                              generated, frontierBefore, frontierAfter,
                              formatList(recent, len(self.expanded), cutAtStart=True),
                              formatNumber(g), formatNumber(h), formatNumber(f)])

    def finish(self):
        self.file.flush()


#####################################################
#                Search algorithms                  #
#####################################################

def depthFirstSearch(problem: SearchProblem):
    """
    Search the deepest nodes in the search tree first.

    Graph search: a state is expanded at most once. The goal test is done when a
    node is popped from the stack, not when it is generated.
    """
    logger = TraceLogger('dfs', problem)
    getState = lambda node: node[0]

    # A node is (state, actions from the start, path cost g, parent state)
    frontier = util.Stack()
    frontier.push((problem.getStartState(), [], 0, None))
    explored = set()

    while not frontier.isEmpty():
        before = frontierSnapshot(frontier, getState)
        state, actions, g, parent = frontier.pop()
        if state in explored:
            continue    # an older copy of a state that was already expanded
        lastAction = actions[-1] if actions else None

        if problem.isGoalState(state):
            logger.log(state, parent, lastAction, 'GOAL', before, frontierSnapshot(frontier, getState), g, 0, g)
            logger.finish()
            return actions

        explored.add(state)
        successors = problem.getSuccessors(state)
        for nextState, action, stepCost in successors:
            if nextState not in explored:
                frontier.push((nextState, actions + [action], g + stepCost, state))
        logger.log(state, parent, lastAction, successors, before, frontierSnapshot(frontier, getState), g, 0, g)

    logger.finish()
    return []   # no path to a goal exists

def breadthFirstSearch(problem: SearchProblem):
    """
    Search the shallowest nodes in the search tree first.

    A state is marked as seen as soon as it is put in the queue, so it can never
    be added twice (once in the frontier or explored, it is skipped).
    """
    logger = TraceLogger('bfs', problem)
    getState = lambda node: node[0]

    start = problem.getStartState()
    frontier = util.Queue()
    frontier.push((start, [], 0, None))
    seen = {start}          # states that are in the frontier or already explored

    while not frontier.isEmpty():
        before = frontierSnapshot(frontier, getState)
        state, actions, g, parent = frontier.pop()
        lastAction = actions[-1] if actions else None

        if problem.isGoalState(state):
            logger.log(state, parent, lastAction, 'GOAL', before, frontierSnapshot(frontier, getState), g, 0, g)
            logger.finish()
            return actions

        successors = problem.getSuccessors(state)
        for nextState, action, stepCost in successors:
            if nextState not in seen:
                seen.add(nextState)
                frontier.push((nextState, actions + [action], g + stepCost, state))
        logger.log(state, parent, lastAction, successors, before, frontierSnapshot(frontier, getState), g, 0, g)

    logger.finish()
    return []

def buildPath(parentOf, state):
    """Follow the parent links back to the start state and return the actions."""
    actions = []
    parent, action = parentOf[state]
    while parent is not None:
        actions.append(action)
        state = parent
        parent, action = parentOf[state]
    actions.reverse()
    return actions

def priorityGraphSearch(problem, name, heuristic, evaluate):
    """
    Graph search with a priority queue. Used by UCS, Greedy Best-First and A*;
    they only differ in the evaluation function used as the priority:
        UCS:  f(n) = g(n)
        GBFS: f(n) = h(n)
        A*:   f(n) = g(n) + h(n)

    Every state is in the queue at most once. When a cheaper path to a state that
    is still in the frontier is found (lower priority), its entry is updated with
    PriorityQueue.update and its parent link is changed to the new path.
    """
    if name != 'ucs':
        name += '-' + getattr(heuristic, '__name__', 'heuristic')
    logger = TraceLogger(name, problem)

    start = problem.getStartState()
    g = {start: 0}                       # cheapest path cost found so far
    h = {start: heuristic(start, problem)}
    parentOf = {start: (None, None)}     # state -> (parent state, action from parent)
    priority = {start: evaluate(0, h[start])}

    frontier = util.PriorityQueue()
    frontier.push(start, priority[start])
    explored = set()

    while not frontier.isEmpty():
        before = frontierSnapshot(frontier)
        state = frontier.pop()
        parent, lastAction = parentOf[state]

        if problem.isGoalState(state):
            logger.log(state, parent, lastAction, 'GOAL', before, frontierSnapshot(frontier),
                       g[state], h[state], priority[state])
            logger.finish()
            return buildPath(parentOf, state)

        explored.add(state)
        successors = problem.getSuccessors(state)
        for nextState, action, stepCost in successors:
            if nextState in explored:
                continue
            newG = g[state] + stepCost
            if nextState not in h:
                h[nextState] = heuristic(nextState, problem)
            newPriority = evaluate(newG, h[nextState])

            if nextState not in priority:
                # first time this state is generated
                frontier.push(nextState, newPriority)
            elif newPriority < priority[nextState]:
                # already waiting in the frontier, but this path is better
                frontier.update(nextState, newPriority)
            else:
                continue
            g[nextState] = newG
            priority[nextState] = newPriority
            parentOf[nextState] = (state, action)

        logger.log(state, parent, lastAction, successors, before, frontierSnapshot(frontier),
                   g[state], h[state], priority[state])

    logger.finish()
    return []

def uniformCostSearch(problem: SearchProblem):
    """Search the node of least total cost first."""
    return priorityGraphSearch(problem, 'ucs', nullHeuristic, lambda g, h: g)

def nullHeuristic(state, problem=None):
    """
    A heuristic function estimates the cost from the current state to the nearest
    goal in the provided SearchProblem.  This heuristic is trivial.
    """
    return 0

def greedyBestFirstSearch(problem: SearchProblem, heuristic=nullHeuristic):
    """Search the node with the lowest heuristic value h(n) first (path cost is ignored)."""
    return priorityGraphSearch(problem, 'gbfs', heuristic, lambda g, h: h)

def aStarSearch(problem: SearchProblem, heuristic=nullHeuristic):
    """Search the node that has the lowest combined cost and heuristic first."""
    return priorityGraphSearch(problem, 'astar', heuristic, lambda g, h: g + h)


# Abbreviations
bfs = breadthFirstSearch
dfs = depthFirstSearch
astar = aStarSearch
ucs = uniformCostSearch
gbfs = greedyBestFirstSearch
