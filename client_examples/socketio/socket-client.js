// Socket.IO Emotion Detection Test Client
let socket = null
let videoElement = null
let overlayCanvas = null
let ctx = null
let frameCounter = 0
let processingInterval = null
let frameRate = 3 // FPS
let isCameraRunning = false
let isProcessing = false

// Theo dõi các face boxes
let currentFaces = {}
let lastUpdateTime = 0
let animationFrameId = null

// DOM elements
document.addEventListener("DOMContentLoaded", () => {
  videoElement = document.getElementById("videoElement")
  overlayCanvas = document.getElementById("overlayCanvas")
  ctx = overlayCanvas.getContext("2d")

  // Buttons
  const connectBtn = document.getElementById("connectBtn")
  const disconnectBtn = document.getElementById("disconnectBtn")
  const startBtn = document.getElementById("startBtn")
  const stopBtn = document.getElementById("stopBtn")

  // Set up event listeners
  connectBtn.addEventListener("click", connectToServer)
  disconnectBtn.addEventListener("click", disconnectFromServer)
  startBtn.addEventListener("click", startProcessing)
  stopBtn.addEventListener("click", stopProcessing)

  // Start camera
  setupCamera()
})

// Function to set up camera
async function setupCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: 640,
        height: 480,
        facingMode: "user",
      },
      audio: false,
    })

    videoElement.srcObject = stream
    videoElement.onloadedmetadata = () => {
      // Cập nhật kích thước canvas overlay để khớp với video
      overlayCanvas.width = videoElement.videoWidth
      overlayCanvas.height = videoElement.videoHeight

      // Bắt đầu render vòng lặp
      startRenderLoop()
    }

    isCameraRunning = true
    logEvent("info", "Camera initialized successfully")
  } catch (error) {
    logEvent("error", `Camera error: ${error.message}`)
  }
}

// Vòng lặp render để vẽ bounding boxes với animation
function startRenderLoop() {
  // Hủy animation frame hiện tại nếu có
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }

  // Hàm render
  function render() {
    // Xóa canvas
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height)

    // Vẽ các bounding boxes hiện tại
    renderFaceBoxes()

    // Tiếp tục vòng lặp render
    animationFrameId = requestAnimationFrame(render)
  }

  // Bắt đầu vòng lặp render
  render()
}

// Connect to Socket.IO server
function connectToServer() {
  const serverUrl = document.getElementById("serverUrl").value
  const token = document.getElementById("token").value

  if (!token) {
    logEvent("error", "JWT token is required for authentication")
    return
  }

  try {
    // Create Socket.IO instance with authentication
    socket = io(serverUrl + "/emotion-detection", {
      path: "/socket.io",
      auth: {
        token: token,
      },
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5,
      transports: ["websocket", "polling"],
    })

    // Attach event handlers
    setupSocketEvents()

    logEvent("info", "Connecting to server...")
    document.getElementById("connectBtn").disabled = true
  } catch (error) {
    logEvent("error", `Connection error: ${error.message}`)
  }
}

// Set up Socket.IO event handlers
function setupSocketEvents() {
  socket.on("connect", () => {
    logEvent("success", `Connected to server with ID: ${socket.id}`)

    // Update UI
    document.getElementById("connectBtn").disabled = true
    document.getElementById("disconnectBtn").disabled = false
    document.getElementById("startBtn").disabled = false

    // Initialize the session
    socket.emit("initialize", {
      client_id: `browser_${Date.now()}`,
      config: {
        video_source: "webcam",
        detection_interval: frameRate,
        min_face_size: 64,
      },
    })
  })

  socket.on("initialized", (data) => {
    logEvent("success", `Session initialized. Session ID: ${data.session_id}`)

    if (data.config && data.config.max_frame_rate) {
      frameRate = Math.min(frameRate, data.config.max_frame_rate)
      logEvent("info", `Using frame rate: ${frameRate} FPS`)
    }
  })

  socket.on("detection_result", (data) => {
    logEvent(
      "info",
      `Received result for frame ${data.frame_id} (${data.faces.length} faces)`
    )
    displayResults(data)

    // Cập nhật bounding boxes với animation
    if (data.faces && data.faces.length > 0) {
      updateFaceBoxes(data.faces)
    } else {
      // Nếu không có khuôn mặt nào được phát hiện, xóa dần dần các box
      fadeFaceBoxes()
    }
  })

  socket.on("status", (data) => {
    logEvent("info", `Server status: ${data.message}`)
  })

  socket.on("error_message", (data) => {
    logEvent("error", `Error (${data.code}): ${data.message}`)

    if (data.code === 429 && data.recommended_value) {
      frameRate = data.recommended_value
      logEvent("info", `Adjusting frame rate to ${frameRate} FPS`)

      // Restart processing with new frame rate
      if (isProcessing) {
        stopFrameProcessing()
        startFrameProcessing()
      }
    }
  })

  socket.on("disconnect", (reason) => {
    logEvent("warning", `Disconnected from server: ${reason}`)

    // Stop processing if it's running
    if (isProcessing) {
      stopProcessing()
    }

    // Update UI
    document.getElementById("connectBtn").disabled = false
    document.getElementById("disconnectBtn").disabled = true
    document.getElementById("startBtn").disabled = true
    document.getElementById("stopBtn").disabled = true
  })

  socket.on("connect_error", (error) => {
    logEvent("error", `Connection error: ${error.message}`)
  })
}

// Disconnect from server
function disconnectFromServer() {
  if (socket) {
    // Stop processing if it's running
    if (isProcessing) {
      stopProcessing()
    }

    socket.disconnect()
    socket = null

    // Update UI
    document.getElementById("connectBtn").disabled = false
    document.getElementById("disconnectBtn").disabled = true
    document.getElementById("startBtn").disabled = true
    document.getElementById("stopBtn").disabled = true

    logEvent("info", "Disconnected from server")
  }
}

// Start emotion detection processing
function startProcessing() {
  if (!socket || !socket.connected) {
    logEvent("error", "Socket not connected. Connect to server first.")
    return
  }

  // Send control event to start processing
  socket.emit("control", {
    action: "start",
    timestamp: Date.now() / 1000,
  })

  // Start sending frames
  startFrameProcessing()

  // Update UI
  document.getElementById("startBtn").disabled = true
  document.getElementById("stopBtn").disabled = false

  logEvent("info", "Started emotion detection processing")
}

// Stop emotion detection processing
function stopProcessing() {
  if (!socket || !socket.connected) {
    return
  }

  // Send control event to stop processing
  socket.emit("control", {
    action: "stop",
    timestamp: Date.now() / 1000,
  })

  // Stop sending frames
  stopFrameProcessing()

  // Update UI
  document.getElementById("startBtn").disabled = false
  document.getElementById("stopBtn").disabled = true

  logEvent("info", "Stopped emotion detection processing")
}

// Start sending video frames
function startFrameProcessing() {
  isProcessing = true
  frameCounter = 0

  // Calculate interval based on frame rate
  const interval = Math.floor(1000 / frameRate)

  processingInterval = setInterval(() => {
    if (videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
      sendVideoFrame()
    }
  }, interval)
}

// Stop sending video frames
function stopFrameProcessing() {
  isProcessing = false
  if (processingInterval) {
    clearInterval(processingInterval)
    processingInterval = null
  }

  // Xóa tất cả các bounding boxes
  currentFaces = {}
}

// Send a single video frame to the server
function sendVideoFrame() {
  try {
    // Tạo canvas ẩn để convert video frame thành base64
    const tempCanvas = document.createElement("canvas")
    tempCanvas.width = videoElement.videoWidth
    tempCanvas.height = videoElement.videoHeight
    const tempCtx = tempCanvas.getContext("2d")
    tempCtx.drawImage(videoElement, 0, 0, tempCanvas.width, tempCanvas.height)

    // Convert canvas to JPEG base64
    const imageData = tempCanvas.toDataURL("image/jpeg", 0.8).split(",")[1]

    // Send frame to server
    socket.emit("video_frame", {
      frame_id: frameCounter++,
      timestamp: Date.now() / 1000,
      resolution: [tempCanvas.width, tempCanvas.height],
      data: imageData,
    })
  } catch (error) {
    logEvent("error", `Error sending frame: ${error.message}`)
  }
}

// Display emotion detection results
function displayResults(data) {
  const facesContainer = document.getElementById("facesContainer")
  facesContainer.innerHTML = ""

  if (!data.faces || data.faces.length === 0) {
    facesContainer.innerHTML = "<p>No faces detected</p>"
    return
  }

  data.faces.forEach((face, index) => {
    const faceDiv = document.createElement("div")
    faceDiv.className = "face"
    faceDiv.innerHTML = `<h3>Face ${index + 1} (ID: ${face.face_id})</h3>`

    // Create emotion bars
    const emotionsDiv = document.createElement("div")
    emotionsDiv.className = "emotions"

    face.emotions.forEach((emotion) => {
      const emotionDiv = document.createElement("div")

      const emotionLabel = document.createElement("div")
      emotionLabel.className = "emotion-label"
      emotionLabel.innerHTML = `<span>${
        emotion.emotion
      }</span><span>${emotion.percentage.toFixed(1)}%</span>`

      const emotionBar = document.createElement("div")
      emotionBar.className = "emotion-bar"
      emotionBar.style.width = `${emotion.percentage}%`

      emotionDiv.appendChild(emotionLabel)
      emotionDiv.appendChild(emotionBar)
      emotionsDiv.appendChild(emotionDiv)
    })

    faceDiv.appendChild(emotionsDiv)
    facesContainer.appendChild(faceDiv)
  })
}

// Cập nhật bounding boxes mới
function updateFaceBoxes(faces) {
  const currentTime = Date.now()
  lastUpdateTime = currentTime

  // Lưu trữ IDs hiện tại để xác định những faces đã không còn
  const currentIds = new Set()

  // Cập nhật hoặc thêm mới faces
  faces.forEach((face) => {
    const faceId = face.face_id
    currentIds.add(faceId)

    // Kiểm tra nếu face đã tồn tại
    if (currentFaces[faceId]) {
      // Face đã tồn tại - lưu vị trí cũ để tạo animation
      const oldFace = currentFaces[faceId]
      oldFace.targetBox = face.box
      oldFace.lastUpdate = currentTime
      oldFace.emotions = face.emotions
    } else {
      // Face mới - thêm vào map với animation bắt đầu
      currentFaces[faceId] = {
        box: face.box, // Hộp hiện tại
        targetBox: face.box, // Hộp đích (cùng - không animation ban đầu)
        emotions: face.emotions,
        lastUpdate: currentTime,
        opacity: 1, // Bắt đầu mờ và sẽ fade in
        isNew: true, // Đánh dấu là đối tượng mới
      }
    }
  })

  // Đánh dấu các faces không còn xuất hiện để fade out
  Object.keys(currentFaces).forEach((faceId) => {
    if (!currentIds.has(faceId)) {
      currentFaces[faceId].isFading = true
      currentFaces[faceId].lastUpdate = currentTime
    }
  })
}

// Fade out dần dần các faces không còn được phát hiện
function fadeFaceBoxes() {
  const currentTime = Date.now()

  // Đánh dấu tất cả các faces để fade out
  Object.keys(currentFaces).forEach((faceId) => {
    currentFaces[faceId].isFading = true
    currentFaces[faceId].lastUpdate = currentTime
  })
}

// Render tất cả face boxes hiện tại
function renderFaceBoxes() {
  const currentTime = Date.now()
  const faceIdsToRemove = []

  // Vẽ các face boxes hiện tại
  Object.entries(currentFaces).forEach(([faceId, face]) => {
    // Tính toán thời gian từ lần cập nhật cuối
    const timeDiff = currentTime - face.lastUpdate

    // Tính toán hộp hiện tại với animation
    let currentBox = face.box
    const targetBox = face.targetBox

    // Hệ số animation giữa 0-1 (hoàn thành sau 300ms)
    const animProgress = Math.min(1, timeDiff / 300)

    // Tính toán vị trí hiện tại dựa trên animation
    if (animProgress < 1) {
      // Nội suy tuyến tính giữa box cũ và box mới
      currentBox = [
        currentBox[0] + (targetBox[0] - currentBox[0]) * animProgress,
        currentBox[1] + (targetBox[1] - currentBox[1]) * animProgress,
        currentBox[2] + (targetBox[2] - currentBox[2]) * animProgress,
        currentBox[3] + (targetBox[3] - currentBox[3]) * animProgress,
      ]
    } else {
      // Animation hoàn thành
      currentBox = targetBox
      face.box = targetBox
    }

    // Vẽ face box với opacity hiện tại
    const [x, y, width, height] = currentBox

    // Lưu trạng thái canvas
    ctx.save()

    // Thiết lập độ mờ
    ctx.globalAlpha = face.opacity

    // Vẽ hộp giới hạn
    ctx.strokeStyle = "#00FF00"
    ctx.lineWidth = 3
    ctx.strokeRect(x, y, width, height)

    // Vẽ face ID
    ctx.fillStyle = "#00FF00"
    ctx.font = "16px Arial"
    ctx.fillText(faceId, x, y - 8)

    // Vẽ emotion chính nếu có
    if (face.emotions && face.emotions.length > 0) {
      const dominantEmotion = face.emotions[0]
      ctx.fillStyle = "rgba(0, 0, 0, 0.7)"
      ctx.fillRect(x, y + height, width, 26)

      ctx.fillStyle = "#FFFFFF"
      ctx.font = "16px Arial"
      ctx.fillText(
        `${dominantEmotion.emotion} (${dominantEmotion.percentage.toFixed(
          1
        )}%)`,
        x + 5,
        y + height + 18
      )
    }

    // Khôi phục trạng thái canvas
    ctx.restore()
  })

  // Xóa các faces đã biến mất hoàn toàn
  faceIdsToRemove.forEach((faceId) => {
    delete currentFaces[faceId]
  })
}

// Log events to the UI
function logEvent(type, message) {
  const logContainer = document.getElementById("logContainer")
  const logEntry = document.createElement("div")
  logEntry.className = `log-entry log-${type}`

  const timestamp = new Date().toLocaleTimeString()
  logEntry.innerHTML = `<strong>[${timestamp}]</strong> ${message}`

  logContainer.appendChild(logEntry)
  logContainer.scrollTop = logContainer.scrollHeight

  // Also log to console
  console.log(`[${type}] ${message}`)
}
