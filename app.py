import json
import os
import streamlit as st
from pyvis.network import Network
from streamlit.components.v1 import html
import pandas as pd

st.set_page_config(layout="wide", page_title="X‑Ray‑Vision")



st.title("X-Ray-Vision")
st.subheader(" :orange[under the guidance of professor mayank]")

DATA_DIR = "test_cases"

LOG_KEYS = [
    "TRACE_REQ_CW_HTTP",
    "TRACE_REQ_CW_STREAM_DIALIN",
    "TRACE_REQ_DW_STREAM_DIALIN",
    "TRACE_REQ_DW_STREAM_SPDY",
    "TRACE_REQ_AW_STREAM_SPDY",
    "TRACE_REQ_AW_STREAM_HTTP",
    "TRACE_REQ_AW_HTTP_UPSTREAM",
    "TRACE_RESP_AW_HTTP_UPSTREAM",
    "TRACE_RESP_AW_STREAM_HTTP",
    "TRACE_RESP_AW_STREAM_SPDY",
    "TRACE_RESP_DW_STREAM_SPDY",
    "TRACE_RESP_DW_STREAM_DIALIN",
    "TRACE_RESP_CW_STREAM_DIALIN",
    "TRACE_RESP_CW_HTTP"
]

def extract_timestamp(log_line):
    if '(' in log_line and ')' in log_line:
        return log_line.split('(')[-1].split(')')[0]
    return None

def parse_log_lines(log_lines):
    result = {}
    for line in log_lines:
        for key in LOG_KEYS:
            if key in line:
                timestamp = extract_timestamp(line)
                result[key] = timestamp
    return result

@st.cache_data
def load_test_cases():
    test_cases = []
    for file in os.listdir(DATA_DIR):
        if file.endswith(".json") and file != "node_metadata.json":
            with open(os.path.join(DATA_DIR, file)) as f:
                data = json.load(f)
                parsed = {"xray_id": data.get("xray_id", "")}
                for key in LOG_KEYS:
                    parsed[key] = "NULL"
                parsed.update(parse_log_lines(data.get("CP - FW Trace", [])))
                parsed.update(parse_log_lines(data.get("CP - DW Trace", [])))
                parsed.update(parse_log_lines(data.get("Connector_trace", [])))
                test_cases.append(parsed)
    return test_cases

trace_data = load_test_cases()
df = pd.DataFrame(trace_data)
st.subheader("Trace Summary Table")
def highlight_null(val): return "background-color: red" if val=="NULL" else ""
st.dataframe(df.style.applymap(highlight_null))


selected_trace_id = st.selectbox("Select X-Ray ID to visualize:", df["xray_id"].tolist())
trace_row = df[df["xray_id"] == selected_trace_id].iloc[0].to_dict()



nodes =["Client","Cloud-Proxy","Connector","Origin-IP"]



net = Network(height="800px", width="100%", directed=True, cdn_resources="remote")

node_positions = {
    "Cloud-Proxy": (-600, 0),
    "Connector": (0, 0),
    "Origin-IP": (600, 0),
}

for node_name, (x, y) in node_positions.items():
    net.add_node(
        node_name,
        label=node_name,
        shape="circle",
        title=f"{node_name}",
        color={
            "border": "#1D9DF9",       
            "background": "#FFFFFF",   
            "highlight": {
                "border": "#004DDC",   
                "background": "#FFFFFF"
            },
            "hover": {
                "border": "#004DDC",
                "background": "#FFFFFF"
            }
        },
        x=x,
        y=y,
        size=100,  
        fixed=True,
        borderWidth=7,
        physics=True
    )


net.toggle_physics(False)

edges=[]

info ="no info yet "
for key, value in trace_row.items():
    if(key=="xray_id" or key=="TRACE_REQ_CW_HTTP"):
        
        continue
    if(key=="TRACE_REQ_CW_STREAM_DIALIN"):
        if(value!="NULL"):
            temp=net.get_node("Cloud-Proxy")
            temp["title"]="CP front worker  has relayed the request to dialin worker at time"+str(value)
        else:
            temp=net.get_node("Cloud-Proxy")
            temp["color"]="red"
            temp["title"]="CP front worker did not relay request to dialin worker"
            info="request was received by the  cloud proxy front worker from the client but could not be relayed to the dialin module hence there is some problem in the cloud proxy "

            break
    if(key=="TRACE_REQ_DW_STREAM_DIALIN"):
        if(value!="NULL"):
            temp=net.get_node("Cloud-Proxy")
            temp["title"]=temp["title"]+"\n dial in worker has received the request from front worker  at time "+str(value)
        else:
            temp["color"]="red"
            temp["title"]=temp["title"]+"\ndial-in worker did not receive request from front worker "
            info="the request is received at the cloud proxy front worker and relayed by the front worker internally but the dialin worker has not received the request there is some problem in the linkage between front worker and dialin worker "
            break
    if(key=="TRACE_REQ_DW_STREAM_SPDY"):
        if(value!="NULL"):
            temp=net.get_node("Cloud-Proxy")
            temp["title"]=temp["title"]+"\n front worker forwarded request over SPDY at time :"+str(value)
        else:
            temp=net.get_node("Cloud_Proxy")
            temp["color"]="red"
            temp["title"]=temp["title"]+"\nrequest could not be sent over spdy by the dialin worker in cloud proxy "
            info="Request has reached cloud proxy dialin worker from the front worker but the dialin worker is not able to send the request to the connector over dialin connection hence the hop to connector is failing "
            break
    if(key=="TRACE_REQ_AW_STREAM_SPDY"):
        if(value!="NULL"):
            edges.append(("Cloud-Proxy","Connector","green","received over dialout from CP at connector"))
        else:
            edges.append(("Cloud-Proxy","Connector","red","did not receive over dialout  at connector"))
            info="The cloud proxy has received the relayed the request using front worker and dialin worker as expected but the connector did not receive the request as shown by the red edge there is loss in between the hop "
            break
    if(key=="TRACE_REQ_AW_STREAM_HTTP"):
        temp=net.get_node("Connector")
        if(value!="NULL"):
            
            temp["title"]=temp["title"]+"\nconnector relayed to internal hop at time :"+str(value)
        else:
            temp["title"]="connector could not relay to the internal hop"
            temp["color"]="red"
            info="The cloud proxy is working fine it received and relayed the request to connector, the request was received by connector as well  but it is not able to complete the internal hop the request was not relayed for the internal hop inside connector "
            break
    if(key=="TRACE_REQ_AW_HTTP_UPSTREAM"):
        temp=net.get_node("Connector")
        if(value!="NULL"):
            temp["title"]="connector has relayed req to origin at time: "+str(value)
            edges.append(("Connector","Origin-IP","green","relayed to origin-IP"))
        else:
            temp["color"]="red"
            edges.append(("Connector","Origin-IP","red","could not relay to origin-IP"))
            temp["title"]="connector is glitching it couldnt relay to origin"
            info="The cloud proxy is working fine it received and relayed the request to connector and the connector has received the request as well but request could not be relayed to the origin by the connector even though internal hop has been completed "
            break
    if(key=="TRACE_RESP_AW_HTTP_UPSTREAM"):
        temp=net.get_node("Origin-IP")
        if(value!="NULL"):
            temp["title"]=temp["title"]+"\norigin-IP workig fine, received and sent response to the connector\n "
            edges.append(("Origin-IP","Connector","green","received from origin-IP"))
        else:
            edges.append(("Origin-IP","Connector","red","did not receive from origin-IP"))
            temp["title"]=temp["title"]+"\n origin has a problem cannot relay response to the connector"
            temp["color"]="red"
            info="The request has been forwarded all the way to the origin and all the components worked correctly but In the response phase The connector has not received any response from the origin as shown by the red edge"
            break
    if(key=="TRACE_RESP_AW_STREAM_HTTP"):
        temp=net.get_node("Connector")
        if(value!="NULL"):
            temp["title"]=temp["title"]+"\nreceived at internal hop at "+str(value)
        else:
            temp["color"]="red"
            temp["title"]=temp["title"]+"\nconnector could not receive response at internal hop"
            info="The request phase has gone correctly all the way to origin but in the response phase Connector is facing an issue as it is not able to complete the internal hop, the response is not received at internal hop even though it was received by connector from origin "
            break
    if(key=="TRACE_RESP_AW_STREAM_SPDY"):
        temp=net.get_node("Connector")
        if(value!="NULL"):
            temp["title"]=temp["title"]+"\nsent response over dialout to CP at "+str(value)
        else:
            temp["color"]="red"
            temp["title"]=temp["title"]+"\ncould not send response over dialout"
            info="In the response phase The connector is malfunctioning it could not send the response over SPDY to the cloud proxy although the internal hop has been completed and it received response from the origin"
            break
    if(key=="TRACE_RESP_DW_STREAM_SPDY"):
        temp=net.get_node("Cloud-Proxy")
        if(value!="NULL"):
            edges.append(("Connector","Cloud-Proxy","green","received by CP over dialin"))
            temp["title"]=temp["title"]+"\n received response over dialin at "+str(value)
        else:
            edges.append(("Connector","Cloud-Proxy","red","did not receive response over dialin "))
            info="The request phase has gone perfectly and the components worked fine but in the response phase we have a problem the response is sent by the connector but is somehow not received by the cloud proxy dial in worker displayed by the red edge hence the response is lost in between "
            break
    if(key=="TRACE_RESP_DW_STREAM_DIALIN"):
        temp=net.get_node("Cloud-Proxy")
        if(value!="NULL"):
            temp["title"]=temp["title"]+"\n response sent by dialin module at time "+str(value)
        else:
            temp["color"]="red"
            temp["title"]=temp["title"]+"\nresponse could not be sent by dialin worker to front worker"
            info ="The request phase gone perfect but in the response phase there is a problem in cloud proxy where the dialin worker could not send the response to the front worker internally"
            break
    if(key=="TRACE_RESP_CW_STREAM_DIALIN"):
        temp=net.get_node("Cloud-Proxy")
        if(value!="NULL"):
            temp["title"]=temp["title"]+"\n response received by front worker at time"+str(value)
        else:
            temp["color"]="red"
            temp["title"]=temp["title"]+"\nresponse not received by front worker "
            info="Request phase was perfect ! In response phase the dialin worker in the cloud proxy has relayed the response to the front worker but it is not received by front worker hence there is some problem in the linkage of these two cloud proxy must be checked  "
            break
    if(key=="TRACE_RESP_CW_HTTP"):
        if(value!="NULL"):
            temp["title"]=temp["title"]+"\n response relayed back to client at "+str(value)
            info="The request and response phases have gone perfectly and there are no problems in any components ! the response has been given back to the client "
        else:
            temp["color"]="red"
            temp["title"]=temp["title"]+"\nresponse not relayed back to client by front worker "
            info="Request and response phases have gone well until the response reached cloud proxy front worker finally where it is not relaying back the response to the client therefore there is a problem with the front worker"
            


for src, dst, color,desc in edges:
    net.add_edge(src, dst, color=color, width=3,title=desc, physics=True)


net.options.edges.smooth = {
    "enabled": True,
    "type": "curvedCW",
    "roundness": 0.25  
}



net.save_graph("trace_graph.html")

with open("trace_graph.html", "r", encoding="utf-8") as f:
    graph_html = f.read()

st.subheader("Request and Response phase")
html(graph_html, height=650)
st.subheader(":orange[Diagnosis :]")
st.subheader(info)
st.markdown("""
<style>
    .css-1kyxreq { background-color: #f9f9f9; border-radius: 8px; padding: 16px; }
    h1 { text-align: center; font-size: 2rem; }
</style>
""", unsafe_allow_html=True)


