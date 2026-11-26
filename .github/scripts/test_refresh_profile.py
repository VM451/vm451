import unittest

from refresh_profile import landmark_repos


def repo(name, pushed, *, updated=None, fork=False, archived=False):
    return {
        "name": name,
        "pushed_at": pushed,
        "updated_at": updated or pushed,
        "fork": fork,
        "archived": archived,
    }


class LandmarkReposTest(unittest.TestCase):
    def test_top_four_use_push_time_not_metadata_update_time(self):
        repos = [
            repo("StaleButEdited", "2026-01-01T00:00:00Z", updated="2026-11-26T00:00:00Z"),
            repo("First", "2026-11-20T00:00:00Z"),
            repo("Fifth", "2026-11-21T00:00:00Z"),
            repo("Second", "2026-11-22T00:00:00Z"),
            repo("Third", "2026-11-24T00:00:00Z"),
            repo("Fourth", "2026-11-25T00:00:00Z"),
        ]

        self.assertEqual(
            [repo["name"] for repo in landmark_repos(repos)],
            ["Fourth", "Third", "Second", "Fifth"],
        )

    def test_excludes_profile_fork_archived_and_empty_repos(self):
        repos = [
            repo("vm451", "2026-11-26T00:00:00Z"),
            repo("Active", "2026-11-20T00:00:00Z"),
            repo("Forked", "2026-11-25T00:00:00Z", fork=True),
            repo("Archived", "2026-11-25T00:00:00Z", archived=True),
            repo("Empty", None),
        ]

        self.assertEqual([repo["name"] for repo in landmark_repos(repos)], ["Active"])

    def test_fractional_push_timestamps_order_correctly(self):
        repos = [
            repo("WholeSecond", "2026-11-25T18:30:35Z"),
            repo("FractionalSecond", "2026-11-25T18:30:35.123Z"),
        ]

        self.assertEqual(
            [repo["name"] for repo in landmark_repos(repos)],
            ["FractionalSecond", "WholeSecond"],
        )


if __name__ == "__main__":
    unittest.main()
