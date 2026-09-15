"""Launch the optional pose-aware local review workflow; no cloud requests."""
import os
import workbench
if __name__ == '__main__':
    os.environ['COUNTBACK_POSE_REVIEW'] = '1'
    print('Pose-aware review enabled. Weak appearance highlights are suppressed; full photographs remain available.', flush=True)
    workbench.main()
