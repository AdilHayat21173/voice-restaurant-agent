# Voice Restaurant Agent 

A real-time AI Voice Assistant for restaurant ordering using the Gemini Live API, Python, and WebSocket-based streaming audio communication.

This project allows users to:

- Talk naturally with an AI restaurant assistant
- Place food orders using voice
- Update existing orders
- Cancel orders
- Check order status
- Stream real-time microphone audio to Gemini Live
- Receive AI-generated voice responses instantly

---

# Features 

✅ Real-time voice conversation  
✅ Gemini Live API integration  
✅ WebSocket-based audio streaming  
✅ Restaurant menu support  
✅ Place orders with AI  
✅ Update existing orders  
✅ Cancel orders  
✅ Check order status  
✅ Voice Activity Detection (VAD)  
✅ Modular project structure  
✅ Tool-based AI architecture  

---

# Project Structure 

```bash
VoiceAgent/
│
├── agents/
│   └── gemini_client.py
│
├── audio/
│   ├── input.py
│   └── output.py
│
├── data/
│   ├── menu.json
│   └── orders.json
│
├── tools/
│   ├── place_order.py
│   ├── cancel_order.py
│   ├── update_order.py
│   └── order_status.py
│
├── utils/
│   ├── validators.py
│   └── file_handler.py
│
├── config.py
├── main.py
├── requirements.txt
├── .env
└── README.md
```

---

# How It Works 

## 1. User Speaks

The microphone captures live audio from the user.

---

## 2. Audio Streaming

Audio is streamed continuously to Gemini Live using real-time WebSocket communication.

---

## 3. Gemini AI Processes Request

The AI understands the user's intent:

- Place order
- Cancel order
- Update order
- Ask menu questions
- Check order status

---

## 4. Tool Execution

Based on the request, the appropriate tool is executed:

- `place_order.py`
- `cancel_order.py`
- `update_order.py`
- `order_status.py`

---

## 5. AI Responds with Voice

Gemini generates a natural voice response back to the user.

---

# Tech Stack 

- Python
- Gemini Live API
- WebSockets
- PyAudio
- AsyncIO
- JSON Storage

---

# Installation 

## 1. Clone Repository

```bash
git clone https://github.com/your-username/voice-restaurant-agent.git
cd voice-restaurant-agent
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Requirements

```bash
pip install -r requirements.txt
```

---

# Environment Variables 

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

Get API key from:

https://aistudio.google.com

---

# Run Project 

```bash
python main.py
```

---

# Example Conversation 

## Place Order

**User:**

> I want one chicken karahi and two naan.

**AI:**

> Your order has been placed successfully. Your order ID is A1.

---

## Update Order

**User:**

> Add one more naan to order A1.

**AI:**

> Your order has been updated successfully.

---

## Cancel Order

**User:**

> Cancel my order A1.

**AI:**

> Your order has been cancelled successfully.

---

## Check Status

**User:**

> What is the status of order A1?

**AI:**

> Your order is currently being prepared.

---

# Important Fixes Included 

## Real-Time Continuous Audio Streaming

Previously:

- Audio chunks were manually filtered
- Second user question was often ignored

Now:

- Continuous audio streaming
- Gemini handles turn detection automatically
- Stable multi-turn conversation support

---

## Better Menu Matching

Improved food matching:

```text
mutton karahi → Mutton Karahi
chicken handi → Chicken Handi
```

---

## Improved Order ID Validation

Supports:

```text
a1
A1
a-1
```

---

## Fixed File Paths

Project now works correctly from any directory.

---

# Requirements 

```txt
google-genai
pyaudio
python-dotenv
numpy
```

---

# Future Improvements 

- Database integration
- FastAPI backend
- React frontend
- Multi-language support
- Order payment integration
- Admin dashboard
- Speech-to-text optimization
- Docker deployment

---

# Author 

Adil Hayat

- AI Engineer
- Generative AI Developer
- Voice AI & Agentic Systems Builder

