// WebRTC Screen Sharing Implementation
let localStream = null;
let peerConnections = {};
let globalParticipants = {};
let myUserId = null;

const ICE_SERVERS = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

// Start screen sharing
async function startPresentation() {
    try {
        console.log('🎥 Starting screen share...');
        
        // Capture screen
        localStream = await navigator.mediaDevices.getDisplayMedia({
            video: { cursor: 'always' },
            audio: false
        });

        console.log('✅ Screen captured');

        // Show local preview
        const videoEl = document.getElementById('presentationVideo');
        if (videoEl) {
            videoEl.srcObject = localStream;
            document.getElementById('presentationArea').style.display = 'flex';
            document.getElementById('stopPresentingBtn').style.display = 'inline-block';
            document.getElementById('presenterName').textContent = 'You are presenting';
        }

        // Handle stream end (user clicks "Stop Sharing" in browser)
        localStream.getVideoTracks()[0].onended = () => {
            console.log('📺 Screen share ended by user');
            stopPresentation();
        };

        // Notify server
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                type: 'start_presentation'
            }));
        }

        // Create peer connections for all participants
        for (const participantId in globalParticipants) {
            if (participantId !== myUserId) {
                await createPeerConnection(participantId, true);
            }
        }

    } catch (error) {
        console.error('❌ Screen share error:', error);
        alert('Failed to start screen sharing. Please allow screen access.');
    }
}

// Stop screen sharing
function stopPresentation() {
    console.log('🛑 Stopping screen share...');

    // Stop local stream
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }

    // Close all peer connections
    for (const peerId in peerConnections) {
        peerConnections[peerId].close();
        delete peerConnections[peerId];
    }

    // Reset UI
    resetPresentationUI();

    // Notify server
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'stop_presentation'
        }));
    }
}

// Reset presentation UI
function resetPresentationUI() {
    const videoEl = document.getElementById('presentationVideo');
    if (videoEl) {
        videoEl.srcObject = null;
    }
    document.getElementById('presentationArea').style.display = 'none';
    document.getElementById('stopPresentingBtn').style.display = 'none';
}

// Create WebRTC peer connection
async function createPeerConnection(peerId, isInitiator) {
    console.log(`🔗 Creating peer connection with ${peerId} (initiator: ${isInitiator})`);

    const pc = new RTCPeerConnection(ICE_SERVERS);
    peerConnections[peerId] = pc;

    // Add local stream tracks
    if (localStream && isInitiator) {
        localStream.getTracks().forEach(track => {
            pc.addTrack(track, localStream);
            console.log(`📤 Added track to peer ${peerId}`);
        });
    }

    // Handle incoming stream
    pc.ontrack = (event) => {
        console.log(`📥 Received track from ${peerId}`);
        const videoEl = document.getElementById('presentationVideo');
        if (videoEl && event.streams[0]) {
            videoEl.srcObject = event.streams[0];
            document.getElementById('presentationArea').style.display = 'flex';
            
            const presenterName = globalParticipants[peerId]?.name || 'Unknown';
            document.getElementById('presenterName').textContent = `${presenterName} is presenting`;
        }
    };

    // Handle ICE candidates
    pc.onicecandidate = (event) => {
        if (event.candidate && socket && socket.readyState === WebSocket.OPEN) {
            console.log(`🧊 Sending ICE candidate to ${peerId}`);
            socket.send(JSON.stringify({
                type: 'signal_ice',
                target: peerId,
                candidate: event.candidate
            }));
        }
    };

    // Handle connection state
    pc.onconnectionstatechange = () => {
        console.log(`🔌 Connection state with ${peerId}: ${pc.connectionState}`);
        if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
            console.warn(`⚠️ Connection with ${peerId} ${pc.connectionState}`);
        }
    };

    // Create offer if initiator
    if (isInitiator) {
        try {
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            
            console.log(`📤 Sending offer to ${peerId}`);
            socket.send(JSON.stringify({
                type: 'signal_offer',
                target: peerId,
                offer: offer
            }));
        } catch (error) {
            console.error(`❌ Error creating offer for ${peerId}:`, error);
        }
    }

    return pc;
}

// Handle WebRTC signaling messages
async function handleSignalMessage(data) {
    const senderId = data.sender;
    
    console.log(`📡 Received ${data.type} from ${senderId}`);

    // Get or create peer connection
    let pc = peerConnections[senderId];
    if (!pc) {
        pc = await createPeerConnection(senderId, false);
    }

    try {
        if (data.type === 'signal_offer') {
            await pc.setRemoteDescription(new RTCSessionDescription(data.offer));
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            
            console.log(`📤 Sending answer to ${senderId}`);
            socket.send(JSON.stringify({
                type: 'signal_answer',
                target: senderId,
                answer: answer
            }));
        }
        else if (data.type === 'signal_answer') {
            await pc.setRemoteDescription(new RTCSessionDescription(data.answer));
        }
        else if (data.type === 'signal_ice') {
            if (data.candidate) {
                await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
                console.log(`✅ Added ICE candidate from ${senderId}`);
            }
        }
    } catch (error) {
        console.error(`❌ Error handling signal from ${senderId}:`, error);
    }
}

console.log('✅ WebRTC Screen Share module loaded');
