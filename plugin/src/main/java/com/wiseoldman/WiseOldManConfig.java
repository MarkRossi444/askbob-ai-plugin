package com.wiseoldman;

import net.runelite.client.config.Config;
import net.runelite.client.config.ConfigGroup;
import net.runelite.client.config.ConfigItem;

@ConfigGroup("wiseoldmanai")
public interface WiseOldManConfig extends Config
{
    @ConfigItem(
        keyName = "apiUrl",
        name = "API URL",
        description = "The URL of the WiseOldMan.Ai backend API. For production, set to your deployed server URL (e.g. https://api.wiseoldman.ai)",
        position = 1
    )
    default String apiUrl()
    {
        return "http://localhost:8001";
    }

    @ConfigItem(
        keyName = "gameMode",
        name = "Game Mode",
        description = "Your account's game mode for tailored advice",
        position = 2
    )
    default GameMode gameMode()
    {
        return GameMode.MAIN;
    }

    enum GameMode
    {
        MAIN("Main"),
        IRONMAN("Ironman"),
        HARDCORE_IRONMAN("Hardcore Ironman"),
        ULTIMATE_IRONMAN("Ultimate Ironman"),
        GROUP_IRONMAN("Group Ironman");

        private final String displayName;

        GameMode(String displayName)
        {
            this.displayName = displayName;
        }

        @Override
        public String toString()
        {
            return displayName;
        }
    }
}
