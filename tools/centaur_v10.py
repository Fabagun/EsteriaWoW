"""Reuse the native-only installer for the female chest-wrap selector collision repair."""

import argparse

import centaur_v9 as deploy

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    args = parser.parse_args()
    deploy.WORK = deploy.deploy.WORK / 'repair-v10'
    if args.action == 'stage':
        deploy.stage('Female Centaur chest wrap isolated from source armored chest/waist outfit 202')
    else:
        deploy.install()
