import astor
import gast


def to_source(node):
    return astor.to_source(gast.gast_to_ast(node))

class SafetyPasser(gast.NodeTransformer):
    def visit_If(self, node):
        self.generic_visit(node)
        node.body.append(gast.Pass())
        node.orelse.append(gast.Pass())
        return node

class ForLoopUnroller(gast.NodeTransformer):
    def make_unrolled_loop(self, node, value_node_list):
        # Repeat the for loop for each element of list, 
        # prepending with a statement "i = next element of iterable"
        unrolled_nodes = []
        for value_node in value_node_list:
            assign_node = gast.Assign(
                targets=[node.target],
                value=value_node)
            unrolled_nodes.append(assign_node)
            unrolled_nodes.extend(node.body)
        return unrolled_nodes

    def visit_For(self, node):
        if isinstance(node.iter, gast.List):
            return self.make_unrolled_loop(node, node.iter.elts)
        elif isinstance(node.iter, gast.Call) and node.iter.func.id == 'range':
            range_args = [arg.n for arg in node.iter.args]
            # manually invoke the range to generate the list of values to use.
            value_node_list = [gast.Num(i) for i in range(*range_args)]
            return self.make_unrolled_loop(node, value_node_list)
        else:
            return node

BOOL_INVERSIONS = {
    gast.Or: gast.And,
    gast.And: gast.Or,
}

class DeMorganFlipper(gast.NodeTransformer):
    def visit_BoolOp(self, node):
        self.generic_visit(node)
        flipped_op = BOOL_INVERSIONS[type(node.op)]
        return gast.UnaryOp(
            op=gast.Not(),
            operand=gast.BoolOp(
                op=flipped_op(),
                values=[gast.UnaryOp(op=gast.Not(), operand=val)
                        for val in node.values]))

OP_INVERSIONS = {
    gast.Eq: gast.NotEq,
    gast.NotEq: gast.Eq,
    gast.Lt: gast.GtE,
    gast.LtE: gast.Gt,
    gast.Gt: gast.LtE,
    gast.GtE: gast.Lt,
    gast.Is: gast.IsNot,
    gast.IsNot: gast.Is,
    gast.In: gast.NotIn,
    gast.NotIn: gast.In,
}

class DoubleNegativeCreator(gast.NodeTransformer):
    def visit_Compare(self, node):
        self.generic_visit(node)
        all_comparators = [node.left] + node.comparators
        if len(all_comparators) == 2:
            # Replace `a < b` with `not a >= b`
            inverted_op = OP_INVERSIONS[type(node.ops[0])]
            return gast.UnaryOp(
                op=gast.Not(),
                operand=gast.Compare(
                    left=node.left,
                    ops=[inverted_op()],
                    comparators=node.comparators))
        else:
            # Replace `a < b < c` with `not (a >= b or b >= c)`
            or_clauses = []
            for left, op, right in zip(
                    all_comparators[:-1],
                    node.ops,
                    all_comparators[1:]):
                inverted_op = OP_INVERSIONS[type(op)]
                or_clauses.append(gast.Compare(
                    left=left,
                    ops=[inverted_op()],
                    comparators=[right]))
            return gast.UnaryOp(
                op=gast.Not(),
                operand=gast.BoolOp(
                    op=gast.Or(),
                    values=or_clauses))


class NodeDepthAnnotator(gast.NodeVisitor):
    def generic_visit(self, node):
        super().generic_visit(node)
        node._statement_depth = 0

    def visit_For(self, node):
        self.generic_visit(node)
        node._statement_depth = 1 + max(
            c._statement_depth
            for c in node.body + node.orelse)

    def visit_If(self, node):
        self.generic_visit(node)
        node._statement_depth = 1 + max(
            c._statement_depth
            for c in node.body + node.orelse)

class IfDepthMaximizer(gast.NodeTransformer):
    def invert(self, node):
      return gast.UnaryOp(op=gast.Not(), operand=node)

    def visit_If(self, node):
        self.generic_visit(node)
        body_depth = max(n._statement_depth for n in node.body)
        orelse_depth = max(n._statement_depth for n in node.orelse)
        if orelse_depth >= body_depth:
            new_node = gast.If(
                test=self.invert(node.test),
                body=node.orelse,
                orelse=node.body)
            # ensure newly created node has a depth annotation too.
            new_node._statement_depth = node._statement_depth
            return new_node
        else:
            return node

def beautify(transforms, source):
    node = gast.parse(source)
    for t in transforms:
        t().visit(node)
    return to_source(node)

