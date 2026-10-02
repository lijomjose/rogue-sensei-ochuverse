import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(ROOT))
from runner import evaluate


class RealCExecutionTests(unittest.TestCase):
    def sample(self, name):
        return (ROOT / "examples" / name).read_text()

    def test_pointer_write_changes_original_across_inputs(self):
        result = evaluate(self.sample("charge_correct.c"))
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual([c["observed"] for c in result["cases"]], [20, 60, 95])
        for case in result["cases"]:
            events = case["events"]
            before, after = events[0], events[-1]
            self.assertEqual(before["object_address"], before["stored_address"])
            self.assertNotEqual(before["pointer_address"], before["object_address"])
            self.assertEqual(before["stored_address"], after["stored_address"])
            local = [e for e in events if e["event"] == "pointer"]
            self.assertNotEqual(local[0]["pointer_address"], before["pointer_address"])
            self.assertEqual(local[0]["stored_address"], before["object_address"])

    def test_equivalent_c_and_parameter_name_are_accepted(self):
        self.assertEqual(evaluate(self.sample("charge_equivalent.c"))["status"],
                         "passed")

    def test_local_pointer_redirection_leaves_caller_and_object_unchanged(self):
        result = evaluate(self.sample("charge_wrong_pointer.c"))
        self.assertEqual(result["status"], "failed")
        for case in result["cases"]:
            self.assertEqual(case["status"], "wrong_result")
            self.assertEqual(case["observed"], case["initial"])
            local = [e for e in case["events"] if e["event"] == "pointer"]
            self.assertIsNone(local[-1]["stored_address"])
            self.assertEqual(case["events"][0]["stored_address"],
                             case["events"][-1]["stored_address"])

    def test_compile_error_is_distinct_from_wrong_result(self):
        self.assertEqual(evaluate("void charge(int *p) { syntax ??? }")["status"],
                         "compile_error")

    def test_null_dereference_has_runtime_diagnostic(self):
        result = evaluate("void charge(int *p) { p = NULL; *p = 20; }")
        self.assertEqual(result["cases"][0]["status"], "runtime_error")
        self.assertTrue(result["cases"][0]["runtime_diagnostics"])

    def test_nonterminating_program_times_out(self):
        result = evaluate("void charge(int *p) { (void)p; for (;;) {} }", timeout=0.2)
        self.assertEqual(result["cases"][0]["status"], "timeout")

    def test_heap_resize_preserves_values_and_release_is_recorded(self):
        result = evaluate(self.sample("heap_lifecycle.c"), demo=True)
        self.assertEqual(result["status"], "passed", result)
        events = result["events"]
        self.assertEqual(events[0]["contents"], "uninitialized")
        self.assertEqual(events[0]["requested_bytes"], 3 * events[0]["element_bytes"])
        self.assertEqual(events[1]["values"], [101, 102, 103])
        self.assertEqual(events[2]["values"], [101, 102, 103, 0, 0])
        self.assertEqual(events[-1]["status"], "freed")
        self.assertIsNone(events[-1]["pointer_value"])


if __name__ == "__main__":
    unittest.main()
