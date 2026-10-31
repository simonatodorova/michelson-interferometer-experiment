"""Run the analysis: `python -m michelson [--out results]`."""
import argparse

from .analysis import analyse


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m michelson", description=__doc__)
    parser.add_argument("--out", default="results", help="folder for results.json and figures")
    parser.add_argument("--data", default="data", help="folder containing clips.csv and tracker/")
    args = parser.parse_args(argv)
    analyse(args.out, args.data)


if __name__ == "__main__":
    main()
