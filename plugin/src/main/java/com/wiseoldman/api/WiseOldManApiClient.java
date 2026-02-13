package com.wiseoldman.api;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonSyntaxException;
import okhttp3.*;

import java.io.IOException;
import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class WiseOldManApiClient
{
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    private static final Gson GSON = new Gson();

    private final OkHttpClient httpClient;
    private final String baseUrl;

    public WiseOldManApiClient(String baseUrl)
    {
        // Strip trailing slash to prevent double-slash URLs
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.httpClient = new OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .build();
    }

    public void askQuestion(String question, String gameMode, List<JsonObject> messages, ApiCallback callback)
    {
        if (question == null || question.trim().isEmpty())
        {
            callback.onError("Please enter a question.");
            return;
        }
        if (gameMode == null || gameMode.trim().isEmpty())
        {
            gameMode = "main";
        }

        JsonObject body = new JsonObject();
        body.addProperty("question", question);
        body.addProperty("game_mode", gameMode);

        if (messages != null && !messages.isEmpty())
        {
            JsonArray messagesArray = new JsonArray();
            for (JsonObject msg : messages)
            {
                messagesArray.add(msg);
            }
            body.add("messages", messagesArray);
        }

        Request request = new Request.Builder()
            .url(baseUrl + "/api/chat")
            .post(RequestBody.create(GSON.toJson(body), JSON))
            .build();

        httpClient.newCall(request).enqueue(new Callback()
        {
            @Override
            public void onFailure(Call call, IOException e)
            {
                String message;
                if (e instanceof ConnectException)
                {
                    message = "Cannot reach the WiseOldMan.Ai server. Is the backend running?";
                }
                else if (e instanceof SocketTimeoutException)
                {
                    message = "Request timed out. The server may be busy.";
                }
                else
                {
                    message = "Connection error: " + e.getMessage();
                }
                callback.onError(message);
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException
            {
                try (ResponseBody responseBody = response.body())
                {
                    if (!response.isSuccessful() || responseBody == null)
                    {
                        String message;
                        switch (response.code())
                        {
                            case 429:
                                message = "Too many requests. Please wait a moment.";
                                break;
                            case 503:
                                message = "Server is starting up. Try again in a few seconds.";
                                break;
                            default:
                                message = "Server error (" + response.code() + ")";
                        }
                        callback.onError(message);
                        return;
                    }

                    String json = responseBody.string();
                    try
                    {
                        JsonObject result = GSON.fromJson(json, JsonObject.class);
                        String answer = result.has("answer")
                            ? result.get("answer").getAsString()
                            : "No response received.";
                        callback.onSuccess(answer);
                    }
                    catch (JsonSyntaxException e)
                    {
                        callback.onError("Received an invalid response from the server.");
                    }
                }
            }
        });
    }

    public void shutdown()
    {
        httpClient.dispatcher().executorService().shutdown();
        httpClient.connectionPool().evictAll();
    }

    public interface ApiCallback
    {
        void onSuccess(String answer);
        void onError(String error);
    }
}
