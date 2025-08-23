/**
 * Simple Postman Test Script for /auth/login endpoint
 * 
 * Minimal script that just extracts and saves the bearer token.
 * Copy this to the "Tests" tab of your login request in Postman.
 */

// Extract and save the bearer token
if (pm.response.code === 200) {
    const responseJson = pm.response.json();
    
    if (responseJson.success && responseJson.data && responseJson.data.access_token) {
        // Save the token as bearerToken variable to COLLECTION
        pm.collectionVariables.set("bearerToken", responseJson.data.access_token);
        
        // Also save to environment as fallback
        pm.environment.set("bearerToken", responseJson.data.access_token);
        
        console.log("✅ Bearer token saved to collection and environment successfully");
        console.log("Token preview:", responseJson.data.access_token.substring(0, 20) + "...");
    } else {
        console.error("❌ Failed to extract token from response");
        console.error("Response structure:", JSON.stringify(responseJson, null, 2));
    }
}