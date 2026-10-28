import json

import pytest

from ers.data.generate import MVP_SCENARIOS, build_scenario, dispatch_code, scenario_to_dict
from ers.data.validate import validate


@pytest.mark.parametrize("name", MVP_SCENARIOS)
@pytest.mark.parametrize("seed", range(5))
def test_generated_scenarios_are_valid(name, seed):
    assert validate(build_scenario(name, seed)) == []


@pytest.mark.parametrize("name", MVP_SCENARIOS)
def test_same_seed_same_data(name):
    a = json.dumps(scenario_to_dict(build_scenario(name, 7)), sort_keys=True)
    b = json.dumps(scenario_to_dict(build_scenario(name, 7)), sort_keys=True)
    assert a == b
    c = json.dumps(scenario_to_dict(build_scenario(name, 8)), sort_keys=True)
    assert a != c


def test_dispatch_code_rules():
    assert dispatch_code("cardiac_arrest", {"red": 1}, 1) == "E"
    assert dispatch_code("entrapment", {"yellow": 3, "green": 4}, 7) == "D"
    assert dispatch_code("stroke", {"yellow": 1}, 1) == "C"
    assert dispatch_code("fall", {"green": 1}, 1) == "A"


def test_call_note_check_and_template():
    from ers.data.call_text import check, facts, template
    inc = next(i for i in build_scenario("s1", 0).incidents if i.needs_rescue)
    f = facts(inc)
    assert check(template(f), f)                                     # the fallback always passes its own check
    addr = f["address"].split(",")[0]
    assert not check(f"{addr}. Crash with {f['n'] + 1} people, some trapped.", f)   # wrong head count
    assert not check(f"Crash with {f['n']} people, some trapped.", f)               # no address
    assert not check(f"{addr}. Crash with {f['n']} people.", f)                     # trapping not mentioned
