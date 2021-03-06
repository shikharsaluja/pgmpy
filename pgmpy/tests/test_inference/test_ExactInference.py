import unittest
import numpy as np
import numpy.testing as np_test
from pgmpy.inference import VariableElimination
from pgmpy.inference import BeliefPropagation
from pgmpy.models import BayesianModel
from pgmpy.models import JunctionTree
from pgmpy.factors import TabularCPD
from pgmpy.factors import Factor


class TestVariableElimination(unittest.TestCase):
    def setUp(self):
        self.bayesian_model = BayesianModel([('A', 'J'), ('R', 'J'), ('J', 'Q'),
                                             ('J', 'L'), ('G', 'L')])
        cpd_a = TabularCPD('A', 2, [[0.2], [0.8]])
        cpd_r = TabularCPD('R', 2, [[0.4], [0.6]])
        cpd_j = TabularCPD('J', 2,
                           [[0.9, 0.6, 0.7, 0.1],
                            [0.1, 0.4, 0.3, 0.9]],
                           ['R', 'A'], [2, 2])
        cpd_q = TabularCPD('Q', 2,
                           [[0.9, 0.2],
                            [0.1, 0.8]],
                           ['J'], [2])
        cpd_l = TabularCPD('L', 2,
                           [[0.9, 0.45, 0.8, 0.1],
                            [0.1, 0.55, 0.2, 0.9]],
                           ['G', 'J'], [2, 2])
        cpd_g = TabularCPD('G', 2, [[0.6], [0.4]])
        self.bayesian_model.add_cpds(cpd_a, cpd_g, cpd_j, cpd_l, cpd_q, cpd_r)

        self.bayesian_inference = VariableElimination(self.bayesian_model)

    # All the values that are used for comparision in the all the tests are
    # found using SAMIAM (assuming that it is correct ;))

    def test_query_single_variable(self):
        query_result = self.bayesian_inference.query(['J'])
        np_test.assert_array_almost_equal(query_result['J'].values,
                                          np.array([0.416, 0.584]))

    def test_query_multiple_variable(self):
        query_result = self.bayesian_inference.query(['Q', 'J'])
        np_test.assert_array_almost_equal(query_result['J'].values,
                                          np.array([0.416, 0.584]))
        np_test.assert_array_almost_equal(query_result['Q'].values,
                                          np.array([0.4912, 0.5088]))

    def test_query_single_variable_with_evidence(self):
        query_result = self.bayesian_inference.query(variables=['J'],
                                                     evidence={'A': 0, 'R': 1})
        np_test.assert_array_almost_equal(query_result['J'].values,
                                          np.array([0.60, 0.40]))

    def test_query_multiple_variable_with_evidence(self):
        query_result = self.bayesian_inference.query(variables=['J', 'Q'],
                                                     evidence={'A': 0, 'R': 0,
                                                               'G': 0, 'L': 1})
        np_test.assert_array_almost_equal(query_result['J'].values,
                                          np.array([0.818182, 0.181818]))
        np_test.assert_array_almost_equal(query_result['Q'].values,
                                          np.array([0.772727, 0.227273]))

    def test_max_marginal(self):
        np_test.assert_almost_equal(self.bayesian_inference.max_marginal(), 0.1659, decimal=4)

    def test_max_marginal_var(self):
        np_test.assert_almost_equal(self.bayesian_inference.max_marginal(['G']), 0.5714, decimal=4)

    def test_max_marginal_var1(self):
        np_test.assert_almost_equal(self.bayesian_inference.max_marginal(['G', 'R']),
                                    0.4055, decimal=4)

    def test_max_marginal_var2(self):
        np_test.assert_almost_equal(self.bayesian_inference.max_marginal(['G', 'R', 'A']),
                                    0.3260, decimal=4)

    def test_map_query(self):
        map_query = self.bayesian_inference.map_query()
        self.assertDictEqual(map_query, {'A': 1, 'R': 1, 'J': 1, 'Q': 1, 'G': 0,
                                         'L': 0})

    def test_map_query_with_evidence(self):
        map_query = self.bayesian_inference.map_query(['A', 'R', 'L'],
                                                      {'J': 0, 'Q': 1, 'G': 0})
        self.assertDictEqual(map_query, {'A': 1, 'R': 0, 'L': 0})


class TestBeliefPropagation(unittest.TestCase):
    def setUp(self):
        self.junction_tree = JunctionTree([(('A', 'B'), ('B', 'C')),
                                           (('B', 'C'), ('C', 'D'))])
        phi1 = Factor(['A', 'B'], [2, 3], range(6))
        phi2 = Factor(['B', 'C'], [3, 2], range(6))
        phi3 = Factor(['C', 'D'], [2, 2], range(4))
        self.junction_tree.add_factors(phi1, phi2, phi3)
        self.belief_propagation = BeliefPropagation(self.junction_tree)

    def test_calibrate_clique_belief(self):
        self.belief_propagation.calibrate()
        clique_belief = self.belief_propagation.get_clique_beliefs()

        phi1 = Factor(['A', 'B'], [2, 3], range(6))
        phi2 = Factor(['B', 'C'], [3, 2], range(6))
        phi3 = Factor(['C', 'D'], [2, 2], range(4))

        b_A_B = phi1 * (phi3.marginalize('D', inplace=False) *
                        phi2).marginalize('C', inplace=False)
        b_B_C = phi2 * (phi1.marginalize('A', inplace=False) *
                        phi3.marginalize('D', inplace=False))
        b_C_D = phi3 * (phi1.marginalize('A', inplace=False) *
                        phi2).marginalize('B', inplace=False)

        np_test.assert_array_almost_equal(clique_belief[('A', 'B')].values,
                                          b_A_B.values)
        np_test.assert_array_almost_equal(clique_belief[('B', 'C')].values,
                                          b_B_C.values)
        np_test.assert_array_almost_equal(clique_belief[('C', 'D')].values,
                                          b_C_D.values)

    def test_calibrate_sepset_belief(self):
        self.belief_propagation.calibrate()
        sepset_belief = self.belief_propagation.get_sepset_beliefs()

        phi1 = Factor(['A', 'B'], [2, 3], range(6))
        phi2 = Factor(['B', 'C'], [3, 2], range(6))
        phi3 = Factor(['C', 'D'], [2, 2], range(4))

        b_B = (phi1 * (phi3.marginalize('D', inplace=False) *
                       phi2).marginalize('C', inplace=False)).marginalize(
            'A', inplace=False)

        b_C = (phi2 * (phi1.marginalize('A', inplace=False) *
                       phi3.marginalize('D', inplace=False))).marginalize(
            'B', inplace=False)

        np_test.assert_array_almost_equal(sepset_belief[frozenset('B')].values,
                                          b_B.values)
        np_test.assert_array_almost_equal(sepset_belief[frozenset('C')].values,
                                          b_C.values)
