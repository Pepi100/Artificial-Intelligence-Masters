from typing import List, Dict, Tuple, Any, Iterator
from bayes_net import BayesNet, BayesNode
from itertools import product
import numpy as np
from argparse import ArgumentParser, Namespace


def read_samples(file_name: str) -> List[Dict[str, int]]:
    samples = []
    with open(file_name, "r") as handler:
        lines = handler.readlines()
        # read first line of file to get variables in order
        variables = [str(v) for v in lines[0].split()]

        for i in range(1, len(lines)):
            vals = [int(v) for v in lines[i].split()]
            sample = dict(zip(variables, vals))
            samples.append(sample)

    return samples


class MLEBayesNet(BayesNet):
    """
    Placeholder class for the Bayesian Network that will learn CPDs using the frequentist MLE
    """
    def __init__(self, bn_file: str="data/bnet"):
        super(MLEBayesNet, self).__init__(bn_file=bn_file)
        self._reset_cpds()

    def _reset_cpds(self) -> None:
        """
        Reset the conditional probability distributions to a value of 0.5
        The values have to be **learned** from the samples.
        """
        for node_name in self.nodes:
            self.nodes[node_name].cpd["prob"] = 0.5

    def learn_cpds(self, samples: List[Dict[str, int]], alpha: float = 1.0) -> None:
        # TODO: YOUR CODE HERE
        pass



def get_args() -> Namespace:
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-f", "--file",
                            type=str,
                            default="data/bn_learning",
                            dest="file_name",
                            help="Input file")
    arg_parser.add_argument("-s", "--samplefile",
                            type=str,
                            default="data/samples_bn_learning",
                            dest="samples_file_name",
                            help="Samples file")
    
    return arg_parser.parse_args()


def main():
    args = get_args()
    table_bn = BayesNet(bn_file=args.file_name)
    mle_bn = MLEBayesNet(bn_file=args.file_name)

    print("Initial params MLE bn:")
    mle_bn.pretty_print()

    print("========== Frequentist MLE ==========")
    samples = read_samples(args.samples_file_name)
    mle_bn.learn_cpds(samples)

    print("Reference BN")
    table_bn.pretty_print()

    print("MLE BayesNet after learning CPDs")
    mle_bn.pretty_print()


if __name__ == "__main__":
    main()
