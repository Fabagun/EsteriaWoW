"""Reuse native-only deployment for the captured female flight event-track crash."""

import argparse

import centaur_v9 as deploy

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    args = parser.parse_args()
    deploy.WORK = deploy.deploy.WORK / 'repair-v11'
    deploy.NATIVE = ('Engine/Source/Model2/M2Data.h', 'Engine/Source/Model2/M2Model.cpp',
                     'Engine/Source/Retail/Centaur.h', 'Tools/RetailAssets/tests.cpp')
    if args.action == 'stage':
        deploy.stage('Bounded M2 event lookup for short female Centaur tracks during flight-form transitions',
                     'centaur_flight_event_guard')
    else:
        deploy.install()
