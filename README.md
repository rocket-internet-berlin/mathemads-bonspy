# Bonspy

Bonspy converts bidding trees from various input formats to the
[Bonsai bidding language of AppNexus](http://blog.appnexus.com/2015/introducing-appnexus-programmable-bidder/).

As intermediate format bonspy constructs a [NetworkX](https://networkx.github.io/) graph from which it produces the
Bonsai language output.
Bidding trees may also be constructed directly in this NetworkX format (see first example below).

At present bonspy provides a converter from trained [sklearn](http://scikit-learn.org/stable/) logistic regression
classifiers with categorical, one-hot encoded features to the intermediate NetworkX format (see second example below).

This package was developed and tested on Python 3.5.
However, the examples below have been tested successfully in Python 2.7.

## Example: NetworkX tree to Bonsai output

    import networkx as nx

    from bonspy import BonsaiTree
    
    
    g = nx.DiGraph()
    
    g.add_node(0,  split='segment', state={})
    g.add_node(1,  split='age', state={'segment': 12345})
    g.add_node(2,  split='age', state={'segment': 67890})
    g.add_node(3,  split='geo', state={'segment': 12345, 'age': (None, 10.)})
    g.add_node(4,  split='geo', state={'segment': 12345, 'age': (10., None)})
    g.add_node(5,  split='geo', state={'segment': 67890, 'age': (None, 10.)})
    g.add_node(6,  split='geo', state={'segment': 67890, 'age': (10., None)})
    g.add_node(7,  is_leaf=True, output=0.10, state={'segment': 12345, 'age': (None, 10.), 'geo': ('UK', 'DE')})
    g.add_node(8,  is_leaf=True, output=0.20, state={'segment': 12345, 'age': (None, 10.), 'geo': ('US', 'BR')})
    g.add_node(9,  is_leaf=True, output=0.10, state={'segment': 12345, 'age': (10., None), 'geo': ('UK', 'DE')})
    g.add_node(10, is_leaf=True, output=0.20, state={'segment': 12345, 'age': (10., None), 'geo': ('US', 'BR')})
    g.add_node(11, is_leaf=True, output=0.10, state={'segment': 67890, 'age': (None, 10.), 'geo': ('UK', 'DE')})
    g.add_node(12, is_leaf=True, output=0.20, state={'segment': 67890, 'age': (None, 10.), 'geo': ('US', 'BR')})
    g.add_node(13, is_leaf=True, output=0.10, state={'segment': 67890, 'age': (10., None), 'geo': ('UK', 'DE')})
    g.add_node(14, is_leaf=True, output=0.20, state={'segment': 67890, 'age': (10., None), 'geo': ('US', 'BR')})
    g.add_node(15, is_default_leaf=True, output=0.05, state={})
    g.add_node(16, is_default_leaf=True, output=0.05, state={'segment': 12345})
    g.add_node(17, is_default_leaf=True, output=0.05, state={'segment': 67890})
    g.add_node(18, is_default_leaf=True, output=0.05, state={'segment': 12345, 'age': (None, 10.)})
    g.add_node(19, is_default_leaf=True, output=0.05, state={'segment': 12345, 'age': (10., None)})
    g.add_node(20, is_default_leaf=True, output=0.05, state={'segment': 67890, 'age': (None, 10.)})
    g.add_node(21, is_default_leaf=True, output=0.05, state={'segment': 67890, 'age': (10., None)})
    
    g.add_edge(0, 1, value=12345, type='assignment')
    g.add_edge(0, 2, value=67890, type='assignment')
    g.add_edge(1, 3, value=(None, 10.), type='range')
    g.add_edge(1, 4, value=(10., None), type='range')
    g.add_edge(2, 5, value=(None, 10.), type='range')
    g.add_edge(2, 6, value=(10., None), type='range')
    g.add_edge(3, 7, value=('UK', 'DE'), type='membership')
    g.add_edge(3, 8, value=('US', 'BR'), type='membership')
    g.add_edge(4, 9, value=('UK', 'DE'), type='membership')
    g.add_edge(4, 10, value=('US', 'BR'), type='membership')
    g.add_edge(5, 11, value=('UK', 'DE'), type='membership')
    g.add_edge(5, 12, value=('US', 'BR'), type='membership')
    g.add_edge(6, 13, value=('UK', 'DE'), type='membership')
    g.add_edge(6, 14, value=('US', 'BR'), type='membership')
    g.add_edge(0, 15)
    g.add_edge(1, 16)
    g.add_edge(2, 17)
    g.add_edge(3, 18)
    g.add_edge(4, 19)
    g.add_edge(5, 20)
    g.add_edge(6, 21)
    
    tree = BonsaiTree(g)

This `tree` looks as follows:

![tree_example](https://cloud.githubusercontent.com/assets/3273502/10993831/4cf94712-8472-11e5-8256-4f736814d7eb.png)

Note that non-leaf nodes track the next user variable to be split on in their `split` attribute while
the current choice of user features is tracked in their `state` attribute.
Leaves designate their output (the bid) in their `output` attribute.

The Bonsai text representation of the above `tree` is stored in its `.bonsai` attribute:

    print(tree.bonsai)
    
prints out

    if segment 12345:
        if segment 12345 age <= 10:
            if geo in ('US', 'BR'):
                0.2000
            elif geo in ('UK', 'DE'):
                0.1000
            else:
                0.0500
        elif segment 12345 age > 10:
            if geo in ('UK', 'DE'):
                0.1000
            elif geo in ('US', 'BR'):
                0.2000
            else:
                0.0500
        else:
            0.0500
    elif segment 67890:
        if segment 67890 age <= 10:
            if geo in ('US', 'BR'):
                0.2000
            elif geo in ('UK', 'DE'):
                0.1000
            else:
                0.0500
        elif segment 67890 age > 10:
            if geo in ('UK', 'DE'):
                0.1000
            elif geo in ('US', 'BR'):
                0.2000
            else:
                0.0500
        else:
            0.0500
    else:
        0.0500

## Example: Sklearn logistic regression classifier to Bonsai output

    from bonspy import LogisticConverter
    from bonspy import BonsaiTree

    features = ['segment', 'age', 'geo']

    vocabulary = {
        'segment=12345': 0,
        'segment=67890': 1,
        'age=0': 2,
        'age=1': 3,
        'geo=UK': 4,
        'geo=DE': 5,
        'geo=US': 6,
        'geo=BR': 7
    }

    weights = [.1, .2, .15, .25, .1, .1, .2, .2]
    intercept = .4

    buckets = {
        'age': {
            '0': (None, 10),
            '1': (10, None)
        }
    }

    types = {
        'segment': 'assignment',
        'age': 'range',
        'geo': 'assignment'
    }

    conv = LogisticConverter(features=features, vocabulary=vocabulary,
                             weights=weights, intercept=intercept,
                             types=types, base_bid=2., buckets=buckets)

    tree = BonsaiTree(conv.graph)

    print(tree.bonsai)

Prints out

    if segment 67890:
        if segment 67890 age > 10:
            if geo="US":
                1.4815
            elif geo="UK":
                1.4422
            elif geo="BR":
                1.4815
            elif geo="DE":
                1.4422
            else:
                1.4011
        elif segment 67890 age <= 10:
            if geo="US":
                1.4422
            elif geo="UK":
                1.4011
            elif geo="BR":
                1.4422
            elif geo="DE":
                1.4011
            else:
                1.3584
        else:
            1.2913
    elif segment 12345:
        if segment 12345 age > 10:
            if geo="US":
                1.4422
            elif geo="DE":
                1.4011
            elif geo="UK":
                1.4011
            elif geo="BR":
                1.4422
            else:
                1.3584
        elif segment 12345 age <= 10:
            if geo="US":
                1.4011
            elif geo="DE":
                1.3584
            elif geo="UK":
                1.3584
            elif geo="BR":
                1.4011
            else:
                1.3140
        else:
            1.2449
    else:
        1.1974

## Example: Uploading the Bonsai output to AppNexus

Base64-encode the tree:

    import base64
    encoded = base64.b64encode(tree.bonsai)

Use our [`nexusadspy` library](https://github.com/mathemads/nexusadspy) to
send the `check_tree` dictionary to the AppNexus tree parser and check
for any syntactical errors in the `tree`:

    from nexusadspy import AppnexusClient
    client = AppnexusClient('.appnexus_auth.json')

    check_tree = {
                   "custom-model-parser": {
                        "model_text": encoded
                        }
                   }

    r = client.request('custom-model-parser', 'POST', data=check_tree)

If the AppNexus API does not return an error for our `tree` we can now
upload it as follows:

    custom_model ={
                    "custom_model": {
                        "name": "Insert tree name (visible in the AppNexus advertiser UI)",
                        "member_id":  # add your integer member ID,
                        "advertiser_id": # add your integer advertiser ID,
                        "custom_model_structure": "decision_tree",
                        "model_output": "bid",
                        "model_text": encoded
                        }
                    }

    r = client.request('custom-model', 'POST', data=custom_model)

Check the response `r` for the integer identifier assigned to your bidding tree by AppNexus.
You will use this identifier to set the uploaded tree as bidding tree for your advertising
campaigns in the AppNexus advertiser UI.

For more details see https://wiki.appnexus.com/display/console/AppNexus+Programmable+Bidder.
