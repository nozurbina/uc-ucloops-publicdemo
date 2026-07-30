# -*- coding: utf-8 -*-
"""
The one stylesheet, composed from three files in assets/.

Every page inlines the whole thing in a single `<style>` — there is no .css
request, which is deliberate: the pages are viewed inside an iframe on a host that
serves some static types oddly (see chrome.py on .svg), and one self-contained file
per page has never had a loading order to get wrong.

    humanloops-urbina.css   brand base, shared with the journey-map templates
    supplement.css          the components this generator emits on top of it
    chrome.css              the top chrome (banner + sticky bar); see chrome.py

There used to be a `data/site.css` holding all three concatenated. It drifted: the
published site had five rule fixes that the base file never got, so anyone editing
the base and regenerating would have silently reverted them. Composing at build
time means there is nowhere for that to hide.
"""
import pathlib

ASSETS = pathlib.Path(__file__).resolve().parent / "assets"

PARTS = ("humanloops-urbina.css", "supplement.css", "chrome.css")


def chrome_css():
    """Just the chrome layer.

    The four journey maps carry a frozen copy of this stylesheet — they have no
    generator — so `postbuild/journey-chrome.py` re-appends this over their copy to
    keep their banner in step with everyone else's.
    """
    return (ASSETS / "chrome.css").read_text(encoding="utf-8")


def stylesheet():
    base, supplement, chrome_css = (
        (ASSETS / p).read_text(encoding="utf-8") for p in PARTS)
    # The separators are load-bearing only in that they keep the output stable —
    # don't change them without re-diffing a scratch build against site/.
    return "/* base */\n" + base + "\n" + supplement + chrome_css
