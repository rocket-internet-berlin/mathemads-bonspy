# Bonspy

Bonspy converts bidding trees from various input formats to the
[Bonsai bidding language of AppNexus](http://blog.appnexus.com/2015/introducing-appnexus-programmable-bidder/).

As intermediate format bonspy constructs a [NetworkX](https://networkx.github.io/) graph from which it produces the
Bonsai language output.
Bidding trees may also be constructed directly in this NetworkX format (see first example below).

At present bonspy provides a converter from trained [sklearn](http://scikit-learn.org/stable/) logistic regression
classifiers with categorical, one-hot encoded features to the intermediate NetworkX format (see second example below).

In combination with our AppNexus API wrapper [`nexusadspy`](https://github.com/mathemads/nexusadspy) it is also
straightforward to check your bidding tree for syntactical errors and upload it for real-time bidding (third example below).

This package was developed and tested on Python 3.5.
However, the examples below have been tested successfully in Python 2.7.

## Example: NetworkX tree to Bonsai output

    import networkx as nx
    from bonspy import BonsaiTree
    import numpy as np
    
    
    def generateBucketAPBtree(segmentID, bids, header=''):
        g2 = nx.DiGraph()
    
        nLeafs = len(bids)
    
        g2.add_node(0, split='segment.value', state={'segment': segmentID})
    
        for i in range(nLeafs):
            g2.add_node(i + 1, is_leaf=True, is_smart=True, leaf_name=str(nLeafs - i), value=float(bids[i]),
                        state={'segment': segmentID})
            g2.add_edge(0, i + 1, value=(nLeafs - i, None), type='range')
    
        g2.add_node(nLeafs + 1, is_leaf=True, is_smart=True, is_default_leaf=True, value=0, state={'segment': segmentID})
        g2.add_edge(0, nLeafs + 1, type='assignment')
    
        tree2 = BonsaiTree(g2)
    
        theTreeWithHeader = header + tree2.bonsai
    
        return theTreeWithHeader
    
    
    segmentID = 199
    bids = np.array([0, 0, 0, 1, 2, 3, 4, 0, 0])
    header = '''#Gererated by some optimiser
    #rna: no')'''
    
    theTree = generateBucketAPBtree(segmentID, bids, header)
    print(theTree)


Note that non-leaf nodes track the next user variable to be split on in their `split` attribute while
the current choice of user features is tracked in their `state` attribute.
Leaves designate their output (the bid) in their `output` attribute.

The Bonsai text representation of the above `tree` is stored in its `.bonsai` attribute:

    print(tree.bonsai)
    
prints out

    #Gererated by some optimiser
    #rna: no')
    if segment[199].value >= 9:
        leaf_name: "9"
        value: no_bid
    elif segment[199].value >= 8:
        leaf_name: "8"
        value: no_bid
    elif segment[199].value >= 7:
        leaf_name: "7"
        value: no_bid
    elif segment[199].value >= 6:
        leaf_name: "6"
        value: 1.0000
    elif segment[199].value >= 5:
        leaf_name: "5"
        value: 2.0000
    elif segment[199].value >= 4:
        leaf_name: "4"
        value: 3.0000
    elif segment[199].value >= 3:
        leaf_name: "3"
        value: 4.0000
    elif segment[199].value >= 2:
        leaf_name: "2"
        value: no_bid
    elif segment[199].value >= 1:
        leaf_name: "1"
        value: no_bid
    else:
        value: no_bid

## Other example: 

    nodeMap = {}
    def getNodeID(C, A, R):
        key = str(C) + str(A) + str(R)
    
        if key not in nodeMap.keys():
            node = len(nodeMap)
            nodeMap.update({key: node})
    
        return nodeMap[key]
    
    
    def generateSR_APBtree(segmentIDs, ages, header=''):
        g2 = nx.DiGraph()
    
        nSegments = len(segmentIDs)
        nAges = len(ages)
    
        g2.add_node(getNodeID(0, 0, 0), split='segment', state={})
    
        for iSeg in range(nSegments):
            g2.add_node(getNodeID(iSeg + 1, 0, 0), split='segment.age', state={'segment': segmentIDs[iSeg]})
            g2.add_edge(getNodeID(0, 0, 0), getNodeID(iSeg + 1, 0, 0), value=segmentIDs[iSeg], type='assignment')
            for iAge in range(nAges):
                g2.add_node(getNodeID(iSeg + 1, iAge + 1, 0), is_leaf=True, is_smart=True, leaf_name=str(iAge), value=iAge,
                            state={'segment': segmentIDs[iSeg], 'segment.age': ages[iAge]})
                g2.add_edge(getNodeID(iSeg + 1, 0, 0), getNodeID(iSeg + 1, iAge + 1, 0), value=(iAge, None), type='range',
                            join_statement=True, is_negated=True)
    
            g2.add_node(getNodeID(iSeg + 1, nAges, 0), is_leaf=True, is_smart=True, is_default_leaf=True, value=1,
                        state={'segment': segmentID})
            g2.add_edge(getNodeID(iSeg + 1, 0, 0), getNodeID(iSeg + 1, nAges, 0), type='assignment')
    
        tree2 = BonsaiTree(g2)
    
        theTreeWithHeader = header + tree2.bonsai
    
        return theTreeWithHeader
    
    
    features = {
        'age': [10, 15, 30, 60, 180],
        'recency': [10, 30, 60],
        'geo': ['FR, UK, UA']
    }
    
    segmentIDs = [10898030, 10898031, 10898032]
    ages = [10, 15, 30, 60, 180]
    header = '''#Gererated by some optimiser
    #rna: no\n'''
    
    theTree = generateSR_APBtree(segmentIDs, ages, header=header)
    print(theTree)

Prints out

    #Gererated by some optimiser
    #rna: no
    if segment[10898030]:
    
        if not every segment[10898030].age >= 0:
            leaf_name: "0"
            value: no_bid
        elif not every segment[10898030].age >= 1:
            leaf_name: "1"
            value: 1.0000
        elif not every segment[10898030].age >= 2:
            leaf_name: "2"
            value: 2.0000
        elif not every segment[10898030].age >= 3:
            leaf_name: "3"
            value: 3.0000
        else:
            leaf_name: "4"
            value: 1.0000
    elif segment[10898031]:
    
        if not every segment[10898031].age >= 0:
            leaf_name: "0"
            value: no_bid
        elif not every segment[10898031].age >= 1:
            leaf_name: "1"
            value: 1.0000
        elif not every segment[10898031].age >= 2:
            leaf_name: "2"
            value: 2.0000
        elif not every segment[10898031].age >= 3:
            leaf_name: "3"
            value: 3.0000
        else:
            leaf_name: "4"
            value: 1.0000
    else segment[10898032]:
    
        if not every segment[10898032].age >= 0:
            leaf_name: "0"
            value: no_bid
        elif not every segment[10898032].age >= 1:
            leaf_name: "1"
            value: 1.0000
        elif not every segment[10898032].age >= 2:
            leaf_name: "2"
            value: 2.0000
        elif not every segment[10898032].age >= 3:
            leaf_name: "3"
            value: 3.0000
        else:
            leaf_name: "4"
            value: 1.0000
            
For trees with arbitraty number of features:

    def test():
        from bonspy import LogisticConverter
        from bonspy import BonsaiTree
    
        features = ['segment', 'segment.age', 'campaign', 'campaign.recency']
    
        vocabulary = {
            'segment=10898030': 0,
            'segment=10898031': 1,
            'segment.age=0': 2,
            'segment.age=1': 3,
            'segment.age=2': 4,
            'segment.age=3': 5,
            'campaign=25198998': 6,
            'campaign.recency=10': 7,
            'campaign.recency=20': 8
        }
    
        weights = [.1, .2, .15, .25, .1, .1, .2, .2, .2, .2]
        intercept = .4
    
        buckets = {
            'segment.age': {
                '0': (None, 10),
                '1': (None, 15),
                '2': (None, 30),
                '3': (None, 60)
            }
        }
    
        types = {
            'segment': 'assignment',
            'segment.age': 'range',
            'campaign': 'assignment',
            'campaign.recency': 'assignment'
        }
    
        conv = LogisticConverter(features=features, vocabulary=vocabulary,
                                 weights=weights, intercept=intercept,
                                 types=types, base_bid=2., buckets=buckets)
    
        tree = BonsaiTree(conv.graph)
    
        print(tree.bonsai)
    
    test()
    
Prints out

    if segment[10898030]:
    
        if segment[10898030].age <= 10:
            if campaign[25198998]:
                if campaign[25198998].recency=10:
                    leaf_name: "blah"
                    value: 2.0000
                elif campaign[25198998].recency=20:
                    leaf_name: "blah"
                    value: 2.0000
                else:
                    1.4011
            else:
                1.3140
        elif segment[10898030].age <= 15:
            if campaign[25198998]:
                if campaign[25198998].recency=10:
                    leaf_name: "blah"
                    value: 2.0000
                elif campaign[25198998].recency=20:
                    leaf_name: "blah"
                    value: 2.0000
                else:
                    1.4422
            else:
                1.3584
        elif segment[10898030].age <= 30:
            if campaign[25198998]:
                if campaign[25198998].recency=10:
                    leaf_name: "blah"
                    value: 2.0000
                elif campaign[25198998].recency=20:
                    leaf_name: "blah"
                    value: 2.0000
                else:
                    1.3799
            else:
                1.2913
        elif segment[10898030].age <= 60:
            if campaign[25198998]:
                if campaign[25198998].recency=10:
                    leaf_name: "blah"
                    value: 2.0000
                elif campaign[25198998].recency=20:
                    leaf_name: "blah"
                    value: 2.0000
                else:
                    1.3799
            else:
                1.2913
        else:
            1.2449
    elif segment[10898031]:
    
        if segment[10898031].age <= 10:
            if campaign[25198998]:
                if campaign[25198998].recency=10:
                    leaf_name: "blah"
                    value: 2.0000
                elif campaign[25198998].recency=20:
                    leaf_name: "blah"
                    value: 2.0000
                else:
                    1.4422
            else:
                1.3584
        elif segment[10898031].age <= 15:
            if campaign[25198998]:
                if campaign[25198998].recency=10:
                    leaf_name: "blah"
                    value: 2.0000
                elif campaign[25198998].recency=20:
                    leaf_name: "blah"
                    value: 2.0000
                else:
                    1.4815
            else:
                1.4011
        elif segment[10898031].age <= 30:
            if campaign[25198998]:
                if campaign[25198998].recency=10:
                    leaf_name: "blah"
                    value: 2.0000
                elif campaign[25198998].recency=20:
                    leaf_name: "blah"
                    value: 2.0000
                else:
                    1.4219
            else:
                1.3364
        elif segment[10898031].age <= 60:
            if campaign[25198998]:
                if campaign[25198998].recency=10:
                    leaf_name: "blah"
                    value: 2.0000
                elif campaign[25198998].recency=20:
                    leaf_name: "blah"
                    value: 2.0000
                else:
                    1.4219
            else:
                1.3364
        else:
            1.2913
    else:
        1.1974