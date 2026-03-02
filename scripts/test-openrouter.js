// Test OpenRouter API with Hermes 3 405B
const { OpenRouter } = require("@openrouter/sdk");

async function testOpenRouter() {
    console.log("=".repeat(60));
    console.log("OpenRouter API Test - Hermes 3 405B");
    console.log("=".repeat(60));
    
    const apiKey = process.env.OPENROUTER_API_KEY;
    
    if (!apiKey) {
        console.log("ERROR: OPENROUTER_API_KEY not set");
        return;
    }
    
    console.log(`\nAPI Key: ${apiKey.substring(0, 15)}...`);
    console.log(`Model: nousresearch/hermes-3-llama-3.1-405b:free`);
    
    const openrouter = new OpenRouter({ apiKey });
    
    try {
        console.log("\nSending test request...");
        
        const response = await openrouter.chat.send({
            model: "nousresearch/hermes-3-llama-3.1-405b:free",
            messages: [
                {
                    role: "user",
                    content: "This is a test. Reply 'OK' if working."
                }
            ],
            max_tokens: 10,
        });
        
        console.log("\nSUCCESS! OpenRouter API is working!");
        console.log(`\nResponse: ${response.choices[0]?.message?.content || 'N/A'}`);
        
    } catch (error) {
        console.log(`\nERROR: ${error.message}`);
        console.log("\nPossible causes:");
        console.log("  1. Invalid API key");
        console.log("  2. Insufficient credits");
        console.log("  3. Model unavailable");
        console.log("  4. Network issues");
    }
}

testOpenRouter();
