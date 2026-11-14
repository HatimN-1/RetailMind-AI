from retailmind.retrieval import search_local
from retailmind.agent import classify, investigate


def test_retrieval_contains_local_source():
    results = search_local("Airflow DAG error retry scheduler")
    assert results and any("airflow" in item["source"] for item in results)


def test_guarded_agent_without_database():
    result = investigate("Erreur pipeline Airflow")
    assert result["intent"] == "pipeline"
    assert "aucun journal" in result["answer"].lower()
    assert result["sources"]


def test_transaction_intent():
    assert classify("Diagnostic TX-0000005") == "transaction"


def test_question_limits():
    try:
        investigate("x" * 2001)
    except ValueError:
        pass
    else:
        raise AssertionError("Should reject overlong question")
