

// Fetch program data from database
async function getProgramDataFromAPI(query) {
    console.log("Sending query to Flask DB:", query);

    try {
        const response = await fetch("http://127.0.0.1:5005/get_program_data", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: query.toLowerCase().trim() })

        });

        if (!response.ok) {
            console.warn("API error:", response.status);
            return null;
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error("Failed to fetch from Flask API:", error);
        return null;
    }
}
// To fetch the name of youtube channel
async function fetchChannelName(videoId) {
    const API_KEY = "AIzaSyDzRaUaAojHpcyGfN8Vid9RkIkw89_pZRU";
    const apiUrl = `https://www.googleapis.com/youtube/v3/videos?part=snippet&id=${videoId}&key=${API_KEY}`;
    try {
        const response = await fetch(apiUrl);
        const data = await response.json();
        if (data.items && data.items.length > 0) {
            return data.items[0].snippet.channelTitle.toLowerCase();
        }
    } catch (err) {
        console.error("YouTube API Error:", err);
    }
    return null;
}

// Send new video to be analyzed 
function sendToFlaskAPI(videoUrl, channelName, videoTitle) {
    chrome.storage.local.get(['userEmail'], function(result) {
        const email = result.userEmail;

        if (!email) {
            console.warn("No email found in Chrome storage.");
            return;
        }
        fetch("http://127.0.0.1:8890/receive_video", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                video_url: videoUrl,
                email: email,                // Dynamically fetched
                channel_name: channelName,
                video_title: videoTitle
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error("Server returned an error: " + response.status);
            }
            return response.json();
        })
        .then( async data => {
            const result = data.analysis;
            if (!result) {
                console.warn(" No analysis returned from Flask.");
                return;
            }
            console.log("Flask API result:", result);

            const stimulation = result.final_stimulation?.toLowerCase() || "unknown";
            if (stimulation.includes("high")) {
                console.warn(" Overstimulating video detected by Flask.");
            
                const animationStyle = result.animation_style || "general";  // Use what Flask returns, or default
            
                await handleHighStimulationFallback(animationStyle);
            
            } else {
                console.log("Flask marked video as safe.");
            }
        })
        .catch(error => {
            console.error("Flask API request failed:", error);
        });
    });
}
//Find fallback shows for redirection 
async function handleHighStimulationFallback(animationStyle) {
    const fallback = await getFallbackByStyle(animationStyle);

    if (fallback && fallback.program) {
        const fallbackSearchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(fallback.program)}`;
        console.log("Redirecting to fallback:", fallbackSearchUrl);
        chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
            chrome.tabs.update(tabs[0].id, { url: fallbackSearchUrl });
        });
    } else {
        console.warn(" No fallback found. No redirection.");
    }
}


//Fetch the animation style from database for redirection
async function getFallbackByStyle(animationStyle) {
    try {
        const response = await fetch("http://127.0.0.1:5005/get_fallback_by_style", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ animation_style: animationStyle.toLowerCase().trim() })
        });

        if (!response.ok) return null;
        const data = await response.json();
        return data;
    } catch (error) {
        console.error("Failed to fetch fallback:", error);
        return null;
    }
}
// fetch the stimulation style from database for redirection 
async function checkOverstimulation(channelName, videoTitle, videoUrl) {
    const query = videoTitle.toLowerCase().trim() || channelName.toLowerCase().trim();
    console.log("Sending query to Flask DB:", query);

    const result = await getProgramDataFromAPI(query);

    if (result && result.stimulation_level) {
        console.log(`From DB: ${result.program}, Level: ${result.stimulation_level}, Style: ${result.animation_style}`);

        // Log existing video into database
        chrome.storage.local.get(['userEmail'], function(storeResult) {
            const email = storeResult.userEmail;
        
            if (!email) {
                console.warn(" No email found in Chrome storage.");
                return;
            }
        
            // Define action_taken based on stimulation level
            let action_taken = "غير محدد";  // Default: Undefined
            if (result.stimulation_level.toLowerCase().includes("high")) {
                action_taken = "إعادة توجيه";  // Redirected
            } else if (
                result.stimulation_level.toLowerCase().includes("medium") ||
                result.stimulation_level.toLowerCase().includes("low") ||
                result.stimulation_level.toLowerCase().includes("moderate")
            ) {
                action_taken = "استمرار بالمشاهدة";  // Continue Watching
            }
        
            fetch("http://127.0.0.1:5005/log_existing_video", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    email: email,
                    channel_name: channelName,
                    youtube_title: videoTitle,
                    youtube_url: videoUrl,
                    stimulation_level: result.stimulation_level,
                    action_taken: action_taken
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log("Existing video logged:", data);
            })
            .catch(error => {
                console.error("Failed to log existing video:", error);
            });
        });
        

        // Redirect if high stimulation
        if (result.stimulation_level.toLowerCase().includes("high")) {
            await handleHighStimulationFallback(result.animation_style);
        } else {
            console.log("Video is safe.");
        }
        

    } else {
        console.warn("Not found in DB. Sending to Flask analyzer...");
        sendToFlaskAPI(videoUrl, channelName, videoTitle);
    }
}
let lastCheckedVideoId = null;

// Watch YouTube tab changes
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === "complete" && tab.url.includes("youtube.com/watch")) {

        const videoId = extractVideoId(tab.url);

        if (!videoId) return;

        // Prevent duplicate checks using videoId
        if (videoId === lastCheckedVideoId) {
            console.log("Skipping duplicate check for Video ID:", videoId);
            return;
        }

        lastCheckedVideoId = videoId;  // Update last checked video ID
        console.log(" YouTube video detected:", tab.url);

        fetchChannelName(videoId).then(channel => {
            if (channel) {
                console.log("Fetched Channel Name:", channel);
                const videoTitle = tab.title.replace(" - YouTube", "").trim();
                checkOverstimulation(channel, videoTitle, tab.url);
            }
        });
    }
});

function extractVideoId(url) {
    const match = url.match(/[?&]v=([^&]+)/);
    return match ? match[1] : null;
}

