import pytest

from ers.data.generate import build_scenario
from ers.env.simulator import Simulation
from ers.eval.metrics import compute_metrics
from ers.messaging.schema import Message
from ers.policies.ma import MultiAgentPolicy


@pytest.mark.parametrize("negotiate", [True, False])
@pytest.mark.parametrize("scenario", ["s1", "s3", "s5"])
def test_mock_agents_run_end_to_end(scenario, negotiate):
    pol = MultiAgentPolicy(negotiate=negotiate, backend="mock")
    sim = Simulation(build_scenario(scenario, 0), pol).run()
    m = compute_metrics(sim)
    assert m["not_transported"] == 0
    assert pol.rt.failures == 0
    assert sim.messages, "agents must exchange messages"
    for msg in sim.messages:                       # every message has the five required fields
        Message(**{k: v for k, v in msg.items() if k != "sim_time"}, sim_time=msg["sim_time"])
        assert msg["sender"] and msg["recipient"] and msg["message_type"] and msg["proposed_action"]
    assert pol.decisions
    assert m["cad_rejections"] == 0                  # every committed action passed the CAD rules


def test_negotiation_only_in_full_ma():
    full = MultiAgentPolicy(negotiate=True, backend="mock")
    Simulation(build_scenario("s5", 1), full).run()
    noneg = MultiAgentPolicy(negotiate=False, backend="mock")
    sim = Simulation(build_scenario("s5", 1), noneg).run()
    assert not any(m["recipient"] == "ResourceAllocation" and m["message_type"] == "REQUEST" for m in sim.messages)
    assert not any(m["message_type"] == "COUNTER" for m in sim.messages if m["sender"] == "HospitalCoordination")
