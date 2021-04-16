from speedwagon.workflows import workflow_verify_checksums

class TestSensitivityComparison:
    def test_sensitive_comparison_valid(self):
        standard_strategy = workflow_verify_checksums.CaseSensitiveComparison()
        assert \
            standard_strategy.compare("asdfasdfasdf", "asdfasdfasdf") is True

    def test_sensitive_comparison_invalid(self):
        standard_strategy = workflow_verify_checksums.CaseSensitiveComparison()
        assert \
            standard_strategy.compare("asdfasdfasdf", "ASDFASDFASDF") is False

    def test_insensitive_comparison_valid(self):
        case_insensitive_strategy = \
            workflow_verify_checksums.CaseInsensitiveComparison()

        assert case_insensitive_strategy.compare("asdfasdfasdf",
                                                 "asdfasdfasdf") is True

    def test_insensitive_comparison_invalid(self):
        case_insensitive_strategy = \
            workflow_verify_checksums.CaseInsensitiveComparison()
        assert case_insensitive_strategy.compare("asdfasdfasdf",
                                                 "ASDFASDFASDF") is True
