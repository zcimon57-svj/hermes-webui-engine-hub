import pathlib
import tempfile
import unittest
from unittest.mock import patch
from engine_hub.resources import admission_errors,trip_errors,MAX_BYTES,HIGH_BYTES,RESERVE_LINUX,RESERVE_WINDOWS


def good():
    return {'linux_available':6*1024**3,'windows_required':True,'windows_available':3*1024**3,
        'swap_used':0,'owned_bytes':0,'owned_tasks':0}


class ResourceContracts(unittest.TestCase):
    def test_windows_free_does_not_follow_linux_cache(self):
        d=good();d['windows_available']=RESERVE_WINDOWS+1024
        self.assertIn('windows_headroom',admission_errors(d,64*1024**2))

    def test_unknown_windows_refuses(self):
        d=good();d['windows_available']=None
        self.assertIn('windows_measurement_missing',admission_errors(d,1))

    def test_linux_reserve_accounts_for_new_start(self):
        d=good();d['linux_available']=RESERVE_LINUX+1024
        self.assertIn('linux_headroom',admission_errors(d,2048))

    def test_aggregate_reservations_not_per_process_limit(self):
        d=good();d['owned_bytes']=HIGH_BYTES-1024
        self.assertIn('owned_memory_budget',admission_errors(d,2048))

    def test_swap_pressure_prevents_restart(self):
        d=good();d['swap_used']=2*1024**3
        self.assertIn('swap_pressure',admission_errors(d,1))

    def test_tasks_are_budgeted_before_explosion(self):
        d=good();d['owned_tasks']=180
        self.assertIn('owned_task_budget',admission_errors(d,1))

    def test_normal_admission(self):
        self.assertEqual(admission_errors(good(),64*1024**2),[])

    def test_authorized_expanded_envelope_admits_bounded_workload(self):
        d=good();d['owned_bytes']=1536*1024**2
        self.assertEqual(admission_errors(d,512*1024**2),[])

    def test_large_model_reservation_requires_windows_headroom(self):
        d=good();d['linux_available']=12*1024**3
        self.assertIn('windows_headroom',admission_errors(d,2*1024**3))

    def test_one_gib_windows_available_trips_before_host_exhaustion(self):
        d=good();d['windows_available']=1024**3
        self.assertIn('windows_headroom_or_measurement',trip_errors(d))

    def test_monitor_trips_before_hard_memory_max(self):
        d=good();d['owned_bytes']=HIGH_BYTES
        self.assertLess(HIGH_BYTES,MAX_BYTES)
        self.assertIn('owned_memory_high',trip_errors(d))

    def test_monitor_host_pressure(self):
        d=good();d['linux_available']=RESERVE_LINUX-1
        self.assertIn('linux_headroom',trip_errors(d))

    def test_monitor_unknown_host_refuses(self):
        d=good();d['windows_available']=None
        self.assertIn('windows_headroom_or_measurement',trip_errors(d))


if __name__=='__main__':unittest.main()
