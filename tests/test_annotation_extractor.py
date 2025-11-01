import unittest

from src.readeck_annotation_export.annotation_extractor import extract_readeck_annotations



class TestExtractReadeckAnnotations(unittest.TestCase):
    def test_empty_input_returns_empty_list(self):
        self.assertEqual(extract_readeck_annotations(""), [])

    def test_single_annotation_plain_text(self):
        html = '<rd-annotation data-annotation-id-value="id1">hello</rd-annotation>'
        out = extract_readeck_annotations(html)
        self.assertEqual(out, ["hello"])

    def test_annotation_with_section_context(self):
        html = (
            "<section>"
            "<div><p><rd-annotation data-annotation-id-value=\"id2\">A</rd-annotation></p></div>"
            "</section>"
        )
        out = extract_readeck_annotations(html)
        # annotation sits inside a section; extractor should emit tags after the last <section>
        self.assertEqual(out, ["<div><p>A</p></div>"])

    # Probably not the optimal behavior, but this test documents current behavior
    # It should work assuming the annotations are always 'contiguous' in the source
    def test_multiple_occurrences_same_id_merge_contexts(self):
        html = (
            "<section><div><p>"
            '<rd-annotation data-annotation-id-value="same">one</rd-annotation>'
            "</p></div></section>"
            "<div><p>"
            '<rd-annotation data-annotation-id-value="same">two</rd-annotation>'
            "</p></div>"
        )
        out = extract_readeck_annotations(html)
        # both occurrences share the same context (div,p) -> should be merged into single wrapper
        self.assertEqual(out, ["<div><p>onetwo</p></div>"])

    def test_preserve_entities_and_charrefs(self):
        html = '<rd-annotation data-annotation-id-value="e1">&amp; &#169;</rd-annotation>'
        out = extract_readeck_annotations(html)
        self.assertEqual(out, ["&amp; &#169;"])

    def test_order_by_first_seen(self):
        html = (
            '<rd-annotation data-annotation-id-value="b">B</rd-annotation>'
            '<rd-annotation data-annotation-id-value="a">A</rd-annotation>'
        )
        out = extract_readeck_annotations(html)
        # first seen b then a -> order should reflect that
        self.assertEqual(out, ["B", "A"])

    def test_complex_example(self):
        # load html from ./tests/complex-example.html
        with open("tests/complex-example.html", "r", encoding="utf-8") as f:
            html = f.read()
        out = extract_readeck_annotations(html)
        expected = [
"""<div><p>The stereotype about monad explanations is that they fall into two buckets: either comparisons to some kind of <a href="https://blog.plover.com/prog/burritos.html" rel="nofollow noopener noreferrer">food item</a>, or throwing complex mathematical jargon at you, <a href="https://stackoverflow.com/questions/3870088/a-monad-is-just-a-monoid-in-the-category-of-endofunctors-whats-the-problem" rel="nofollow noopener noreferrer"><em>what’s the problem?</em></a></p></div>""",
"""<div><p>But monads aren’t esoteric or magical at all, nor do they only occur in functional programming. In essence, a monad is a <em>design pattern</em> that allows you to chain together operations within a framework. Noticing monadic design can be quite helpful for programmers in any environment, particularly because it’s often <strong>undesirable</strong>! In many situations, monads have observable tradeoffs, and sometimes (as here) we can even collect concrete data to back this up.</p></div>""",
"""<div><h2 id="hL.WCag.1-property-based-testing">1. Property-based testing</h2></div>""",
"""<div><p>Testing is fundamentally about building models for how your code should behave, at just the right level of complexity: they should match the scope of what you’re testing, without going overboard and reinventing the whole system a second time.</p></div>""",
"""<div><p>Nothing quite exemplifies testing-as-modeling like property-based testing—an approach where instead of specifying exact examples, you define models in terms of <strong>properties</strong>, or invariants, that your code should satisfy. Then, you test your models against randomly generated inputs.</p></div>""",
"""<div><p>Example-based tests are quite valuable, because they are easy to write and quite direct about what happens. But even in a simple example like sorting, it’s easy to imagine cases where your examples don’t quite cover every edge case.</p></div>""",
"""<div><p>This example is quite unhelpful and hard to understand! It is possible to use this as an input to debug with, but it is quite painful. If we could use automation to turn this test case into a much smaller one that can still reproduce the bug, debugging becomes significantly easier. The process of doing so is called test case <strong>shrinking</strong> or <strong>reduction</strong>.</p></div>""",
"""<div><p>To recap—property-based testing consists of two components:</p><ul><li>Test case </li></ul><ul><li><strong>generation</strong></li></ul><ul><li> using a source of randomness.</li></ul><ul><li>On failing a test, </li></ul><ul><li><strong>shrinking</strong></li></ul><ul><li> it down to a smaller, more understandable size.</li></ul></div>""",
"""<div><h3 id="hL.WCag.implementing-a-manual-shrinker">Implementing a manual shrinker</h3></div>""",
"""<div><p>What counts as “smaller”? For a list of numbers, ideally we’d be able to minimize both the number of items in the list and the integers themselves. This suggests an algorithm for how to write a shrinker by hand:</p></div>""",
"""<div><ul><li><p>First, try and minimize the size of the list using a binary search algorithm.</p></li></ul></div>""",
"""<div><ul><li><p>Once the list has been shrunk, start shrinking the elements within the list, applying binary search to each element.</p></li></ul></div>""",
"""<div><h2 id="hL.WCag.2-drawing-the-rest-of-the-owl">2. Drawing the rest of the owl</h2></div>""",
"""<div><p>Trying to think of all the different failure modes seems really hard! But property-based testing can address this need through randomized <strong>fault injection</strong>.</p></div>""",
"""<div><p>Let’s focus on Ord safety for now, with a comparator that flips around the result 20% of the time:</p></div>""",
"""<div><div><pre tabindex="0"><code><span><span><span>#[derive(Clone, Copy, Debug)]</span><span>
</span><span>enum</span> <span>OrdBehavior</span><span> </span><span>{</span><span>
</span><span>    </span><span>Regular</span><span>,</span><span>
</span><span>    </span><span>Flipped</span><span>,</span><span>
</span><span>}</span><span>
</span><span>
</span><span>struct</span> <span>BadType</span><span> </span><span>{</span><span>
</span><span>    </span><span>value</span>: <span>u64</span><span>,</span><span>
</span><span>    </span><span>ord_behavior</span>: <span>RefCell</span><span>&lt;</span><span>Vec</span><span>&lt;</span><span>OrdBehavior</span><span>&gt;&gt;</span><span>,</span><span>
</span><span>}</span><span>
</span><span>
</span><span>impl</span><span> </span><span>Ord</span><span> </span><span>for</span><span> </span><span>BadType</span><span> </span><span>{</span><span>
</span><span>    </span><span>fn</span> <span>cmp</span><span>(</span><span>&amp;</span><span>self</span><span>,</span><span> </span><span>other</span>: <span>&amp;</span><span>Self</span><span>)</span><span> </span>-&gt; <span>Ordering</span><span> </span><span>{</span><span>
</span><span>        </span><span>// Get the next behavior from the list.
</span><span>        </span><span>match</span><span> </span><span>self</span><span>.</span><span>ord_behavior</span><span>.</span><span>borrow_mut</span><span>().</span><span>pop</span><span>()</span><span> </span><span>{</span><span>
</span><span>            </span><span>Some</span><span>(</span><span>OrdBehavior</span>::<span>Regular</span><span>)</span><span> </span><span>|</span><span> </span><span>None</span><span> </span><span>=&gt;</span><span> </span><span>{</span><span>
</span><span>                </span><span>self</span><span>.</span><span>value</span><span>.</span><span>cmp</span><span>(</span><span>&amp;</span><span>other</span><span>.</span><span>value</span><span>)</span><span>
</span><span>            </span><span>}</span><span>
</span><span>            </span><span>OrdBehavior</span>::<span>Flipped</span><span> </span><span>=&gt;</span><span> </span><span>{</span><span>
</span><span>                </span><span>// Flip the behavior.
</span><span>                </span><span>other</span><span>.</span><span>value</span><span>.</span><span>cmp</span><span>(</span><span>&amp;</span><span>self</span><span>.</span><span>value</span><span>)</span><span>
</span><span>            </span><span>}</span><span>
</span><span>        </span><span>}</span><span>
</span><span>    </span><span>}</span><span>
</span><span>}</span></span></span></code></pre></div></div>""",
"""<div><p>To generate a <code>BadType</code>:</p></div>""",
"""<div><div><pre tabindex="0"><code><span><span><span>fn</span> <span>generate_bad_type</span><span>()</span><span> </span>-&gt; <span>BadType</span><span> </span><span>{</span><span>
</span><span>    </span><span>// Generate a value between 0 and 10000;
</span><span>    </span><span>let</span><span> </span><span>value</span><span> </span><span>=</span><span> </span><span>/* ... */</span><span>;</span><span>
</span><span>    </span><span>// Generate a list of behaviors of length 0..128, where the elements are
</span><span>    </span><span>// Regular 4/5 times and Flipped 1/5 times.
</span><span>    </span><span>let</span><span> </span><span>ord_behavior</span>: <span>Vec</span><span>&lt;</span><span>OrdBehavior</span><span>&gt;</span><span> </span><span>=</span><span> </span><span>/* ... */</span><span>;</span><span>
</span><span>
</span><span>    </span><span>BadType</span><span> </span><span>{</span><span>
</span><span>        </span><span>value</span><span>,</span><span>
</span><span>        </span><span>ord_behavior</span>: <span>RefCell</span>::<span>new</span><span>(</span><span>ord_behavior</span><span>),</span><span>
</span><span>    </span><span>}</span><span>
</span><span>}</span></span></span></code></pre></div></div>""",
"""<div><p>Our original approach continues to work well—that is, right until the test finds a bug and we need to shrink a failing input.</p></div>""",
"""<div><h2 id="hL.WCag.3-integrated-shrinking">3. Integrated shrinking</h2></div>""",
"""<div><p>The practical result is that most of the time, writing a shrinker for types like </p><p><code>Vec&lt;BadType&gt;</code></p><p> is quite difficult. And writing one is also technically optional, since:</p><ul><li>If the test passes, shrinkers are never invoked. Simply write correct code, and shrinking just isn’t an issue!</li></ul><ul><li>If the test fails, developers can debug using the original input. It’s painful but possible.</li></ul></div>""",
"""<div><p>most modern property-based testing frameworks, like <a href="https://docs.rs/proptest" rel="nofollow noopener noreferrer"><strong>proptest</strong></a> in Rust, try and take care of shrinking for you through some notion of <em>integrated shrinking</em>.</p></div>""",
"""<div><p>The idea behind integrated shrinking is: When you generate a random input, you don’t just generate the value itself. You also generate some context that is helpful for reducing the size of the input.</p></div>""",
"""<div><ul><li>In proptest, this combined value and context is called a <a href="https://docs.rs/proptest/latest/proptest/strategy/trait.ValueTree.html" rel="nofollow noopener noreferrer"><strong>value tree</strong></a>.Any implementation that accepts a random number generator and turns it into a value tree is called a <a href="https://docs.rs/proptest/latest/proptest/strategy/trait.Strategy.html" rel="nofollow noopener noreferrer"><strong>strategy</strong></a>.</li></ul></div>""",
"""<div><ul><li>The <a href="https://docs.rs/proptest/latest/proptest/macro.prop_oneof.html" rel="nofollow noopener noreferrer"><strong><code>prop_oneof</code></strong></a><a href="https://docs.rs/proptest/latest/proptest/macro.prop_oneof.html" rel="nofollow noopener noreferrer"><strong> strategy</strong></a>, which generates values from one of a possible list of strategies, where each choice has a given probability. (A function that takes one or more strategies as input, and produces a strategy as its output, is called a <strong>combinator</strong>.)</li></ul></div>""",
"""<div><div><pre tabindex="0"><code><span><span><span>fn</span> <span>generate_ord_behavior</span><span>()</span><span> </span>-&gt; <span>impl</span><span> </span><span>Strategy</span><span>&lt;</span><span>Value</span><span> </span><span>=</span><span> </span><span>OrdBehavior</span><span>&gt;</span><span> </span><span>{</span><span>
</span><span>    </span><span>prop_oneof!</span><span>[</span><span>
</span><span>        </span><span>// 4/5 chance that the Regular implementation is generated.
</span><span>        </span><span>4</span><span> </span><span>=&gt;</span><span> </span><span>Just</span><span>(</span><span>OrdBehavior</span>::<span>Regular</span><span>),</span><span>
</span><span>        </span><span>// 1/5 chance that it&#39;s flipped.
</span><span>        </span><span>1</span><span> </span><span>=&gt;</span><span> </span><span>Just</span><span>(</span><span>OrdBehavior</span>::<span>Flipped</span><span>),</span><span>
</span><span>    </span><span>]</span><span>
</span><span>}</span></span></span></code></pre></div></div>""",
"""<div><p>You might be wondering where all the shrinking code is. It’s actually implemented on the corresponding value trees for each strategy:</p><ul><li>Range strategies use binary search to make values smaller.</li></ul><ul><li>The </li></ul><ul><li><code>Just</code></li></ul><ul><li> strategy doesn’t do any shrinking, since it just returns a single value.</li></ul><ul><li>The </li></ul><ul><li><code>prop_oneof</code></li></ul><ul><li> combinator shrinks towards the beginning of the choices: in this case, </li></ul><ul><li><code>Flipped</code></li></ul><ul><li> is shrunk into </li></ul><ul><li><code>Regular</code></li></ul><ul><li>.</li></ul><ul><li>The </li></ul><ul><li><code>vec</code></li></ul><ul><li> combinator implements roughly the algorithm in </li></ul><ul><li><a href="https://sunshowers.io/posts/monads-through-pbt/%23implementing-a-manual-shrinker" rel="nofollow noopener noreferrer"><em>Implementing a manual shrinker</em></a></li></ul><ul><li> above.</li></ul></div>""",
"""<div><p>In my experience, composability across different scales is where this model shines. You can build bigger strategies out of smaller ones, up to a surprising amount of complexity. This means that your team can invest in a library of ever-more-complex strategies, and continue to derive value out of that library across everything from the smallest of unit tests to large integration tests.</p></div>""",
"""<div><p>But there is one <em>massive</em> wrinkle with integrated shrinking. And that wrinkle is <em>exactly</em> what monads are about.</p></div>""",
"""<div><h2 id="hL.WCag.4-monads-finally">4. Monads, finally</h2></div>"""
        ]
        self.assertEqual(out, expected)



if __name__ == "__main__":
    unittest.main()
