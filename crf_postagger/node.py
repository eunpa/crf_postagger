import re
from collections import namedtuple
from .common import bos, eos, unk
from .lemmatizer import lemma_candidate

doublespace_pattern = re.compile(u'\s+', re.UNICODE)
Node = namedtuple('Node', 'words first_word last_word first_tag last_tag begin end node_score')

class BaseNodeGenerator:
    def __init__(self, pos2words, state_features, max_word_len=0):
        self.pos2words = pos2words
        self.state_features = state_features
        self.max_word_len = max_word_len

        if self.max_word_len == 0:
            self._check_max_word_len()

    def _check_max_word_len(self):
        if not self.pos2words:
            raise ValueError('pos2words should not be empty')
        self.max_word_len = max(
            max(len(word) for word in words) for words in self.pos2words.values())

    def generate(self, sentence):
        # prepare lookup list
        chars = sentence.replace(' ','')
        sent = self._sentence_lookup(sentence)
        n_char = len(sent) + 1

        # add end node
        eos_node = Node(eos, eos, None, eos, None, n_char-1, n_char, 0)
        sent.append([eos_node])

        # check first word position
        nonempty_first = self._get_nonempty_first(sent, n_char)
        if nonempty_first > 0:
            # (words, first_word, last_word, first_tag, last_tag, begin, end, node_score)
            word = chars[:nonempty_first]
            sent[0] = [Node(word, word, word, unk, unk, 0, nonempty_first, 0)]

        # add link between adjacent nodes
        edges = self._link_adjacent_nodes(sent, chars, n_char)

        for edge in edges:
            print(edge[0])
            print(edge[1], end='\n\n')
        # add link from unk node
        edges = self._link_from_unk_nodes(edges, sent)

        bos_node = Node(bos, None, bos, None, bos, 0, 0, 0)
        for word in sent[0]:
            edges.append((bos_node, word))
        edges = sorted(edges, key=lambda x:(x[0].begin, x[1].end))

        return edges, bos_node, eos_node

    def _get_nonempty_first(self, sent, end, offset=0):
        for i in range(offset, end):
            if sent[i]:
                return i
        return offset

    def _link_adjacent_nodes(self, sent, chars, n_char):
        edges = []
        for words in sent[:-1]:
            for word in words:
                if not sent[word.end]:
                    unk_end = self._get_nonempty_first(sent, n_char, word.end)
                    unk_word = chars[word.end:unk_end]
                    unk_node = Node(unk_word, unk_word, unk_word, unk, unk, word.end, unk_end, 0)
                    edges.append((word, unk_node))
                for adjacent in sent[word.end]:
                    edges.append((word, adjacent))
        return edges

    def _link_from_unk_nodes(self, edges, sent):
        unk_nodes = {to_node for _, to_node in edges if to_node.last_tag == unk}
        for unk_node in unk_nodes:
            for adjacent in sent[unk_node.end]:
                edges.append((unk_node, adjacent))
        return edges

    def _sentence_lookup(self, sentence):
        sentence = doublespace_pattern.sub(' ', sentence)
        sent = []
        for eojeol in sentence.split():
            sent += self._word_lookup(eojeol, offset=len(sent))
        return sent

    def _word_lookup(self, eojeol, offset=0):
        n = len(eojeol)
        pos = [[] for _ in range(n)]
        for b in range(n):
            for r in range(1, self.max_word_len+1):
                e = b+r
                if e > n:
                    continue
                sub = eojeol[b:e]
                for tag, score in self._get_pos(sub):
                    pos[b].append(Node(sub, sub, sub, tag, tag, b+offset, e+offset, score))
                for lemma_node in self._add_lemmas(sub, r, b, e, offset):
                    pos[b].append(lemma_node)
        return pos

    def _get_pos(self, word):
        return [(tag, words[word]) for tag, words in self.pos2words.items() if word in words]

    def _add_lemmas(self, sub, r, b, e, offset):
        for i in range(1, min(self.max_word_len, len(sub)) + 1):
            try:
                for l_morph, r_morph, l_tag, r_tag, score in self._lemmatize(sub, i):
                    node = Node(
                        l_morph + ' + ' + r_morph,
                        l_morph, r_morph, l_tag, r_tag, b+offset, e+offset,
                        score
                    )
                    yield node
            except Exception as e:
                print(e)
                continue

    def _lemmatize(self, word, i):
        l = word[:i]
        r = word[i:]
        lemmas = []
        len_word = len(word)
        for l_, r_ in lemma_candidate(l, r):
            if (l_ in self.pos2words.get('Verb', {})) and (r_ in self.pos2words.get('Eomi', {})):
                yield (l_, r_, 'Verb', 'Eomi', self.pos2words['Verb'][l_] + self.pos2words['Eomi'][r_])
            if (l_ in self.pos2words.get('Adjective', {})) and (r_ in self.pos2words.get('Eomi', {})):
                yield (l_, r_, 'Adjective', 'Eomi', self.pos2words['Adjective'][l_] + self.pos2words['Eomi'][r_])
            if len_word > 1 and not (word in self.pos2words.get('Noun', {})):
                if (l_ in self.pos2words['Noun']) and (r_ in self.pos2words['Josa']):
                    yield (l_, r_, 'Noun', 'Josa', self.pos2words['Noun'][l_] + self.pos2words['Josa'][r_])