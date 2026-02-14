package com.askbob;

import com.google.gson.JsonObject;
import com.askbob.api.AskBobApiClient;

import javax.inject.Inject;
import java.awt.image.BufferedImage;

import net.runelite.api.Client;
import net.runelite.api.events.GameTick;
import net.runelite.client.callback.ClientThread;
import net.runelite.client.events.ConfigChanged;
import net.runelite.client.eventbus.Subscribe;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;
import net.runelite.client.ui.ClientToolbar;
import net.runelite.client.ui.NavigationButton;
import net.runelite.client.util.ImageUtil;

@PluginDescriptor(
    name = "AskBob.Ai",
    description = "AI-powered OSRS expert chatbot backed by the full OSRS wiki",
    tags = {"ai", "chat", "wiki", "helper", "guide"}
)
public class AskBobPlugin extends Plugin
{
    private static final int CONTEXT_UPDATE_INTERVAL = 5; // Update every 5 game ticks (~3 seconds)

    @Inject
    private Client client;

    @Inject
    private AskBobConfig config;

    @Inject
    private ClientToolbar clientToolbar;

    @Inject
    private ClientThread clientThread;

    private AskBobPanel panel;
    private NavigationButton navButton;
    private AskBobApiClient apiClient;

    @Override
    protected void startUp() throws Exception
    {
        apiClient = new AskBobApiClient(config.apiUrl());

        panel = new AskBobPanel(config);
        panel.setApiClient(apiClient);

        final BufferedImage icon = ImageUtil.loadImageResource(getClass(), "icon.png");

        navButton = NavigationButton.builder()
            .tooltip("AskBob.Ai")
            .icon(icon)
            .priority(5)
            .panel(panel)
            .build();

        clientToolbar.addNavigation(navButton);
    }

    @Subscribe
    public void onGameTick(GameTick event)
    {
        if (client.getTickCount() % CONTEXT_UPDATE_INTERVAL != 0)
        {
            return;
        }

        JsonObject ctx = PlayerContextBuilder.build(client);
        if (panel != null && ctx != null)
        {
            panel.setPlayerContext(ctx);
        }
    }

    @Subscribe
    public void onConfigChanged(ConfigChanged event)
    {
        if (!"askbobai".equals(event.getGroup()))
        {
            return;
        }

        if ("apiUrl".equals(event.getKey()))
        {
            if (apiClient != null)
            {
                apiClient.shutdown();
            }
            apiClient = new AskBobApiClient(config.apiUrl());
            if (panel != null)
            {
                panel.setApiClient(apiClient);
            }
        }
    }

    @Override
    protected void shutDown() throws Exception
    {
        clientToolbar.removeNavigation(navButton);
        if (apiClient != null)
        {
            apiClient.shutdown();
        }
        panel = null;
        apiClient = null;
    }
}
