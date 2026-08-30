"""
Unit tests for Live Scores and Snapshot Persistence
===================================================
"""

import pytest
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from live_scores import MatchSnapshot, MatchEvent


def test_match_snapshot_creation():
    snapshot = MatchSnapshot(
        match_id=12345,
        home_team="Arsenal",
        away_team="Chelsea",
        status="IN_PLAY",
        home_score=1,
        away_score=0,
        competition="Premier League",
        minute=35,
        timestamp=time.time()
    )
    
    assert snapshot.match_id == 12345
    assert snapshot.home_team == "Arsenal"
    d = snapshot.to_dict()
    assert d['home_score'] == 1
    assert d['status'] == "IN_PLAY"


def test_match_event_enum():
    assert MatchEvent.GOAL_HOME.value == "goal_home"
    assert MatchEvent.GOAL_AWAY.value == "goal_away"
    assert MatchEvent.RED_CARD.value == "red_card"
    assert MatchEvent.FULLTIME.value == "fulltime"
