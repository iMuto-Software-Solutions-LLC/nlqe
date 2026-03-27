from query_engine.synthesis.answer import AnswerSynthesizer


def test_format_answer():
    answer = "The total sales were $1000."
    results = [{"sales": 500}, {"sales": 500}]
    execution_time = 123.45

    formatted = AnswerSynthesizer.format_answer(answer, results, execution_time)

    assert "The total sales were $1000." in formatted
    assert "(Query returned 2 results in 123ms)" in formatted


def test_format_answer_no_results():
    answer = "No sales found."
    results = []
    execution_time = 5.2

    formatted = AnswerSynthesizer.format_answer(answer, results, execution_time)

    assert "No sales found." in formatted
    assert "(Query returned 0 results in 5ms)" in formatted
