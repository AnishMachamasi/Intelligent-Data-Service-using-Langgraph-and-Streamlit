BUTTON_STYLE = """
<style>
    .st-emotion-cache-1g9obwo, .st-emotion-cache-jh76sn {
            display:inline-flex; 
            -webkit-box-align:center; 
            align-items:center; 
            -webkit-box-pack:center; 
            justify-content:center; 
            font-weight:400;
            padding:0.25rem 0.75rem;
            border-radius:0.5rem;
            min-height:2.5rem;
            margin:0px;
            line-height:1.6;
            color:inherit; 
            width:auto; 
            cursor:pointer; 
            user-select:none; 
            background-color: rgb(43, 44, 54);
            border:1px solid rgba(250, 250, 250, 0.2);
            margin-top:450px;
            margin-left:95px;
        }
</style>
"""

SIDEBAR_STYLE = """
<style>
    .st-emotion-cache-ri3enp, .st-emotion-cache-f03grt {
        display: inline-flex;
        -webkit-box-align: center;
        align-items: center;
        -webkit-box-pack: center;
        justify-content: center;
        font-weight: 400;
        padding: 0.25rem 0.75rem;
        border-radius: 0.5rem;
        min-height: 2.5rem;
        margin: 0px;
        line-height: 1.6;
        color: inherit;
        cursor: pointer;
        user-select: none;
        background-color: rgb(19, 23, 32);
        border: 1px solid rgba(250, 250, 250, 0.2);

        /* Updated properties for top-right positioning */
        position: fixed; /* Use 'fixed' to stay in place during scrolling */
        top: 60px; /* Distance from the top */
        right: 20px; /* Distance from the right */
        z-index: 9999; /* Ensure it appears above other elements */

        /* Remove width if it's not needed for the top-right corner */
        width: auto; 
    }
</style>
"""

HIDE_STREAMLIT_STYLE = """
<style>
        .st-emotion-cache-janbn0 {
            flex-direction: row-reverse;
            text-align: right;
        }
        [data-testid="stSidebarNav"] {
            background-image: none;
        }
        div[data-testid="stSidebarUserContent"] > div:nth-child(2) {
            position: fixed;
            bottom: 0;
            width: 100%;
            padding-bottom: 1rem;
        }
        [data-testid="stStatusWidget"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
            }
</style>
"""
