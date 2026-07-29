import unittest

from adapter.e5_run_policy import (
    record_tau3_db_sanity,
    run_case_attempts,
    summarize_framework_sweep,
)


class TestE5RunPolicy(unittest.TestCase):
    def test_error_is_retried_once(self) -> None:
        results = iter([{"verdict": "error"}, {"verdict": "pass"}])
        attempts = run_case_attempts(lambda: next(results))
        self.assertEqual([item["verdict"] for item in attempts], ["error", "pass"])

    def test_fail_is_not_retried(self) -> None:
        attempts = run_case_attempts(lambda: {"verdict": "fail"})
        self.assertEqual(len(attempts), 1)

    def test_five_percent_error_guard_is_inclusive(self) -> None:
        one_error = [[{"verdict": "error"}]]
        nineteen_passes = [[{"verdict": "pass"}] for _ in range(19)]
        eighteen_passes = [[{"verdict": "pass"}] for _ in range(18)]
        self.assertTrue(
            summarize_framework_sweep(one_error + nineteen_passes)["valid"]
        )
        self.assertFalse(
            summarize_framework_sweep(one_error + eighteen_passes)["valid"]
        )

    def test_tau3_sanity_is_recorded_without_overriding_verdict(self) -> None:
        run_log = {
            "evaluation": {
                "verdict": "fail",
                "criterion_b": {"met": True},
            }
        }
        result = record_tau3_db_sanity(
            run_log,
            db_match=True,
            db_reward=1.0,
        )
        self.assertEqual(result["evaluation"]["verdict"], "fail")
        self.assertEqual(
            result["sanity"]["tau3_db"],
            {
                "db_match": True,
                "db_reward": 1.0,
                "agrees_with_criterion_b": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
