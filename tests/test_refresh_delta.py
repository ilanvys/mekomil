import unittest

from tools.check_refresh_delta import validate_delta


def manifest(skill_count=100, repo_count=10):
    repos = [f"repo-{i}" for i in range(repo_count)]
    return {
        "org": "skills-il",
        "maxFileBytes": 262144,
        "repos": repos,
        "defaultBranches": {repo: "main" for repo in repos},
        "skills": {
            f"skill-{i}": {
                "repo": repos[i % len(repos)],
                "files": ["SKILL.md", "references/details.md"],
            }
            for i in range(skill_count)
        },
    }


class RefreshDeltaTests(unittest.TestCase):
    def test_ordinary_skill_and_file_deletions_are_allowed(self):
        previous = manifest()
        candidate = manifest(skill_count=99)
        candidate["skills"]["skill-1"]["files"] = ["SKILL.md"]

        self.assertEqual(validate_delta(previous, candidate), [])

    def test_default_branch_change_is_allowed(self):
        previous = manifest()
        candidate = manifest()
        candidate["defaultBranches"]["repo-1"] = "trunk"

        self.assertEqual(validate_delta(previous, candidate), [])

    def test_losing_more_than_a_quarter_of_skills_is_blocked(self):
        failures = validate_delta(manifest(), manifest(skill_count=74))

        self.assertTrue(any("skills" in failure for failure in failures), failures)

    def test_losing_exactly_a_quarter_of_skills_is_allowed(self):
        self.assertEqual(validate_delta(manifest(), manifest(skill_count=75)), [])

    def test_losing_more_than_a_quarter_of_repos_is_blocked(self):
        failures = validate_delta(manifest(), manifest(repo_count=7))

        self.assertTrue(any("repos" in failure for failure in failures), failures)

    def test_identity_change_is_blocked(self):
        previous = manifest()
        candidate = manifest()
        candidate["org"] = "another-org"
        candidate["maxFileBytes"] = 123

        failures = validate_delta(previous, candidate)

        self.assertTrue(any("org" in failure for failure in failures), failures)
        self.assertTrue(any("maxFileBytes" in failure for failure in failures), failures)


if __name__ == "__main__":
    unittest.main()
