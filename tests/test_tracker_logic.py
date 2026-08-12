import unittest
from unittest.mock import patch
from src.core.logic import TrackerLogic
from src.core.profile_manager import Phase, SprintProfile, ProfileManager


class TrackerLogicTests(unittest.TestCase):
    def setUp(self):
        profile_manager = ProfileManager()
        profile_manager.profiles = [
            SprintProfile(
                name="Тест",
                phases=[Phase("sprint", 1), Phase("break", 1)],
                repeat=2,
                id="test-profile",
            )
        ]
        profile_manager.active_profile_id = "test-profile"
        
        self.logic = TrackerLogic(profile_manager=profile_manager)
        self.logic.sound_enabled = False

    @patch("src.core.logic.time.time")
    def test_pause_stops_effective_phase_timer(self, mock_time):
        mock_time.return_value = 100.0
        self.logic.start_session()
        mock_time.return_value = 110.0
        self.logic.toggle_pause()
        mock_time.return_value = 130.0

        self.assertEqual(self.logic.get_effective_phase_time(), 10.0)

        self.logic.toggle_pause()
        mock_time.return_value = 135.0
        self.assertEqual(self.logic.get_effective_phase_time(), 15.0)

    def test_profile_repeat_starts_new_cycle(self):
        self.logic.session_active = True
        self.logic.current_sprint_index = 1
        self.logic.current_cycle = 0

        self.logic._advance_phase()

        self.assertEqual(self.logic.current_cycle, 1)
        self.assertEqual(self.logic.current_sprint_index, 0)
        self.assertEqual(self.logic.current_phase, "sprint")

    def test_restored_session_is_paused(self):
        restored = self.logic.restore_active_session({
            "active": True,
            "started_at": 100.0,
            "points": 12,
            "tab_times": {"Бэкофис панорам": 60.0},
            "current_phase": "sprint",
            "current_sprint_index": 0,
        })

        self.assertTrue(restored)
        self.assertTrue(self.logic.session_active)
        self.assertTrue(self.logic.paused)
        self.assertEqual(self.logic.session_points, 12)

    def test_empty_session_is_not_added_to_history(self):
        self.logic.session_active = True
        self.logic.session_start = 100.0

        self.logic.stop_session()

        self.assertEqual(self.logic.sessions, [])


if __name__ == "__main__":
    unittest.main()
