import {Crawler} from "./crawler"


const span = document.getElementById("current_website");
const hint = document.getElementById("hint");

//query current tab for current url, and rendering logic. 
chrome.tabs.query(
    { active: true, currentWindow: true },
    (tabs) => {
        if (!tabs[0] || !tabs[0].url) {
            span.textContent = "No active urls, but HOW?";
            return;
        }

        const url = tabs[0].url;
        span.textContent = url;

        if (isLikelyRoot(url)) {
            hint.textContent = "Valid Root page.";
        } else {
            hint.textContent = "Not a recognized root page... Consider, finding a better root.";
        }
    }
);


document.addEventListener("DOMContentLoaded", () =>{
    const start = document.getElementById("start");

    start.addEventListener('click', ()=>{
        // alert("yo, btn works");
        if((isLikelyRoot(span.textContent))){
            startRAGpipeline(span.textContent);
            startVisualisation();
        }else if(confirm("Are you sure you want to perform this action?")){
            startRAGpipeline();
            startVisualisation();
        }

    })
})

//to check is current url is root, and thus ready to be crawled.
function isLikelyRoot(urlString) {
    const commonRoots = [
        "/",
        "/docs", "/documentation",
        "/guide", "/guides",
        "/learn",
        "/api", "/api-reference", "/reference",
        "/getting-started",
        "/tutorial", "/tutorials",
        "/examples",
        "/sdk",
        "/developer", "/developers"
    ];

    try {
        const url = new URL(urlString);
        // Normalize: lowercase and remove trailing slash (except for root "/")
        let path = url.pathname.toLowerCase();
        if (path.length > 1 && path.endsWith("/")) {
            path = path.slice(0, -1);
        }

        // 1. Check exact match against common roots
        if (commonRoots.includes(path)) {
            return true;
        }

        // 2. Check for versioned roots (e.g., /3, /v1, /en/latest)
        // Logic: If the path is NOT in our common list, is it a "short" path 
        // that looks like a version or language selector?
        const segments = path.split('/').filter(s => s.length > 0);
        
        // Allow single segment versions (e.g. /3, /v2.0)
        if (segments.length === 1) {
            const first = segments[0];
            // Matches: "3", "v1", "v2.0", "en", "latest"
            if (/^v?\d+(\.\d+)*$/.test(first) || ['en', 'latest', 'main', 'master'].includes(first)) {
                return true;
            }
        }
        
        // Allow double segment versions (e.g., /en/latest, /3.8/)
        if (segments.length === 2) {
             if (['en', 'latest', 'main', 'master'].includes(segments[0]) || /^v?\d+(\.\d+)*$/.test(segments[0])) {
                 return true;
             }
        }

        return false;
    } catch (e) {
        console.error("Invalid URL:", e);
        return false;
    }
}   



function startRAGpipeline(url){
    startCrawl(url);
}

//to show the progress visually in the UI
function startVisualisation(){

}


//start the crawling process, assuming that the 
function startCrawl(url){
    
}