/* UPDATE THESE VALUES TO MATCH YOUR SETUP */

const CONSISTENCY_API_URL = "ec2-44-248-72-237.us-west-2.compute.amazonaws.com/consistency/update"
const PROCESSING_STATS_API_URL = "ec2-44-248-72-237.us-west-2.compute.amazonaws.com/processing/stats"
const ANALYZER_API_URL = {
    stats: "ec2-44-248-72-237.us-west-2.compute.amazonaws.com/analyzer/stats",
    events: "ec2-44-248-72-237.us-west-2.compute.amazonaws.com/analyzer/booking/attraction?index=25",
    tickets: "ec2-44-248-72-237.us-west-2.compute.amazonaws.com/analyzer/buy/tickets?index=25"
}

// This function fetches and updates the general statistics
const makeReq = (url, cb) => {
    fetch(url)
        .then(res => res.json())
        .then((result) => {
            console.log("Received data: ", result)
            cb(result);
        }).catch((error) => {
            updateErrorMessages(error.message)
        })
}

const updateCodeDiv = (result, elemId) => document.getElementById(elemId).innerText = JSON.stringify(result)

const getLocaleDateStr = () => (new Date()).toLocaleString()

const getStats = () => {
    document.getElementById("last-updated-value").innerText = getLocaleDateStr()
    
    makeReq(PROCESSING_STATS_API_URL, (result) => updateCodeDiv(result, "processing-stats"))
    makeReq(ANALYZER_API_URL.stats, (result) => updateCodeDiv(result, "analyzer-stats"))
    makeReq(ANALYZER_API_URL.events, (result) => updateCodeDiv(result, "event-booking"))
    makeReq(ANALYZER_API_URL.tickets, (result) => updateCodeDiv(result, "event-tickets"))
}

const updateErrorMessages = (message) => {
    const id = Date.now()
    console.log("Creation", id)
    msg = document.createElement("div")
    msg.id = `error-${id}`
    msg.innerHTML = `<p>Something happened at ${getLocaleDateStr()}!</p><code>${message}</code>`
    document.getElementById("messages").style.display = "block"
    document.getElementById("messages").prepend(msg)
    setTimeout(() => {
        const elem = document.getElementById(`error-${id}`)
        if (elem) { elem.remove() }
    }, 7000)
}

const setup = () => {
    getStats()
    setInterval(() => getStats(), 4000) // Update every 4 seconds
}

const runConsistencyCheck = () => {
    fetch(CONSISTENCY_API_URL, { method: "POST" })
        .then(res => res.json())
        .then((result) => {
            console.log("Consistency check result: ", result);
            updateCodeDiv(result, "consistency-check-result");
        }).catch((error) => {
            updateErrorMessages(error.message);
        });
}

// Add event listener to the button
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById("run-consistency-check-btn").addEventListener("click", runConsistencyCheck);
});



document.addEventListener('DOMContentLoaded', setup)