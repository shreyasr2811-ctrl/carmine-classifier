"""
Streamlit version compatibility.

Streamlit renamed `use_container_width` to `width="stretch"` in 1.43 and will
eventually drop the old argument; `st.radio` and `st.slider` gained `width` in
the same release and now default to *content* width, which makes a segmented
control collapse to the size of its longest option.

Both call sites (app.py and ui/site.py) need the same shim, so it lives here
rather than being written twice and drifting apart.
"""

import streamlit as st

_SV = tuple(int(p) for p in st.__version__.split(".")[:2] if p.isdigit())

#: spread into st.plotly_chart / st.image / st.button / st.dataframe
WIDE = {"width": "stretch"} if _SV >= (1, 43) else {"use_container_width": True}

#: spread into st.radio / st.slider, which had no width argument before 1.43
STRETCH = {"width": "stretch"} if _SV >= (1, 43) else {}
