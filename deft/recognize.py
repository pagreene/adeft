import logging
from nltk.stem.snowball import EnglishStemmer

from deft.nlp import word_tokenize
from deft.util import contains_shortform, get_max_candidate_longform


logger = logging.getLogger('recognize')

_stemmer = EnglishStemmer()


class _TrieNode(object):
    __slots__ = ['longform', 'children']
    """TrieNode struct for use in recognizer

    Attributes
    ----------
    concept : str|None
        concept has a str value containing an agent ID at terminal nodes of
        the recognizer trie, otherwise it has a None value.

    children : dict
        dict mapping tokens to child nodes
    """
    def __init__(self, longform=None):
        self.longform = longform
        self.children = {}


class LongformRecognizer(object):
    __slots__ = ['shortform', 'exclude', 'longforms', '_trie']
    """Class for recognizing longforms by matching the standard pattern

    Searches text for the pattern "<longform> (<shortform>)" for a collection
    of longforms supplied by the user.

    Parameters
    ----------
    shortform : str
        shortform to be recognized

    longforms : iterable of str
        Contains candidate longforms.

    Attributes
    ----------
    _trie : :py:class:`deft.recognizer.__TrieNode`
        Trie used to search for longforms. Edges correspond to stemmed tokens
        from longforms. They appear in reverse order to the bottom of the trie
        with terminal nodes containing the associated longform in their data.
    """

    def __init__(self, shortform, longforms, exclude=None):
        self.shortform = shortform
        self.longforms = longforms
        self._trie = self._init_trie(longforms)
        if exclude is None:
            self.exclude = set([])
        else:
            self.exclude = exclude

    def recognize(self, sentence):
        """Find longform in sentence by matching the standard pattern

        Parameters
        ----------
        sentence : str
            Sentence where we seek to disambiguate shortform

        Returns
        -------
        longform : str|None
            longform corresponding to shortform in sentence if the standard
            pattern is matched. Returns None if the pattern is not matched
        """
        if not contains_shortform(sentence, self.shortform):
            return
        else:
            # if it does, extract candidate
            candidate = get_max_candidate_longform(sentence, self.shortform)
            longform = self._search(tuple(_stemmer.stem(token)
                                          for token in candidate[::-1]))
            return longform

    def _init_trie(self, longforms):
        """Initialize search trie from iterable of longforms

        Parameters
        ---------
        longforms : iterable of str
            longforms to add to the trie. They will be tokenized and stemmed,
            then their tokens will be added to the trie in reverse order.

        Returns
        -------
        root : :py:class:`deft.recogize._TrieNode`
            Root of search trie used to recognize longforms
        """
        root = _TrieNode()
        for longform in self.longforms:
            edges = tuple(_stemmer.stem(token)
                          for token in word_tokenize(longform))[::-1]
            current = root
            for index, token in enumerate(edges):
                if token not in current.children:
                    if index == len(edges) - 1:
                        new = _TrieNode(longform)
                    else:
                        new = _TrieNode()
                    current.children[token] = new
                    current = new
                else:
                    current = current.children[token]
        return root

    def _search(self, tokens):
        """Returns longform from maximal candidate preceding shortform

        Parameters
        ----------
        tokens : tuple of str
            contains tokens that precede the occurence of the pattern
            "<longform> (<shortform>)" up until the start of the containing
            sentence or an excluded word is reached. Tokens must appear in
            reverse order.

        Returns
        -------
        str|None:
            Agent ID corresponding to associated longform in the concept map
            if one exists, otherwise None.
        """
        current = self._trie
        for token in tokens:
            if token not in current.children:
                break
            if current.children[token].longform is not None:
                return current.children[token].longform
            else:
                current = current.children[token]
        else:
            return None
