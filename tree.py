
class Nodes(object):
    """
    Nodes functionality used by Nodes and Trees
    """
    def addChild(self, child_node):
        """
        Add child node.  Set level, and parent of node.
        Returns child node
        """
        if isinstance(self, NodeTree):
            start_node = self.root_node
        else:
            start_node = self
        child_node.level = start_node.level + 1
        child_node.parent = start_node
        start_node.children.append(child_node)
        return child_node
        
    def getDepth(self):
        "Get tree depth (including root node)"
        if isinstance(self, NodeTree):
            start_node = self.root_node
        else:
            start_node = self
        max_depth = 1 # initialise
        for child_node in start_node.children:
            child_depth = child_node.getDepth()
            if (child_depth + 1) > max_depth:
                max_depth = child_depth + 1
        return max_depth

    def getTerminalNodes(self):
        "Gets list of terminal nodes"
        if isinstance(self, NodeTree):
            if not self.root_node.children:
                raise Exception, "Cannot get terminal nodes until " + \
                    "there is at least one node added to tree"                
            start_node = self.root_node
        else:
            start_node = self            
        if not start_node.children:
            return [start_node]
        else:
            term_nodes_lst = []
            children_term_nodes = \
                [child_node.getTerminalNodes() for child_node in start_node.children]
            for child_term_nodes in children_term_nodes:
                term_nodes_lst += child_term_nodes
            return term_nodes_lst
        
    def generNode(self):
        yield self
        for child_node in self.children:
            for node in child_node.generNode():
                yield node
    
class NodeTree(Nodes):
    """
    Object names follow standard tree data structure terminology of 
    root, nodes, subtrees, terminal nodes, parent, child, sibling, 
    and tree depth.
    Nodes can only have one parent.  All nodes come from root.
    """
    
    def __init__(self):
        self.root_node = Node(label="Root")
        self.root_node.level = 0

    def printChildren(self, node):
        l = []
        for child_node in node.children:
            l.append(unicode(child_node))
            children_str = unicode(self.printChildren(child_node))
            if children_str: #otherwise an empty string will get own line
                l.append(unicode(self.printChildren(child_node)))
        return "\n".join(l)
    
    def __str__(self):
        l = []
        l.append(unicode(self.root_node))
        l.append(self.printChildren(self.root_node))
        return "\n".join(l)
        
class Node(Nodes):
    """
    Optionally, has details (a dictionary) and a text label.    
    Node index is set when added to either a tree 
    or an existing node.
    Parent is set when added to a node (or left as None if added
    to a tree). Children is updated as children are added.
    """
    
    def __init__(self, dets_dic=None, label=""):
        if dets_dic:
            self.dets_dic = dets_dic
        else:
            self.dets_dic = {}
        self.level = None
        self.parent = None
        self.children=[]
        self.label = label
        
    def __str__(self):
        return self.level*2*" " + "Level: " + unicode(self.level) + \
            "; Label: " + self.label + \
            "; Details: " + unicode(self.dets_dic) + \
            "; Child labels: " + ", ".join([x.label for x in self.children])
            