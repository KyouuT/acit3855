import logo from './logo.jpg';
import './App.css';

import EndpointAudit from './components/EndpointAnalyzer'
import AppStats from './components/AppStats'

function App() {

    const endpoints = ["stats", "buy/tickets", "booking/attraction"]

    const rendered_endpoints = endpoints.map((endpoint) => {
        return <EndpointAnalyzer key={endpoint} endpoint={endpoint}/>
    })

    return (
        <div className="App">
            <img src={logo} className="App-logo" alt="logo" height="150px" width="400px"/>
            <div>
                <AppStats/>
                <h1>Analyzer Endpoints</h1>
                {rendered_endpoints}
            </div>
        </div>
    );

}



export default App;
