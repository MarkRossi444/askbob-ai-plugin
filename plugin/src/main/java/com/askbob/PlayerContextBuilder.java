package com.askbob;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import net.runelite.api.Client;
import net.runelite.api.GameState;
import net.runelite.api.Player;
import net.runelite.api.Quest;
import net.runelite.api.QuestState;
import net.runelite.api.Skill;
import net.runelite.api.coords.WorldPoint;

/**
 * Snapshots live player data from the RuneLite Client into a JsonObject.
 * All methods must be called on the game thread (ClientThread).
 */
public final class PlayerContextBuilder
{
    // Achievement diary completion varbit IDs: {easy, medium, hard, elite}
    private static final String[] DIARY_REGIONS = {
        "ardougne", "desert", "falador", "fremennik", "kandarin",
        "karamja", "kourend", "lumbridge", "morytania", "varrock",
        "western", "wilderness"
    };

    private static final int[][] DIARY_VARBITS = {
        {4458, 4459, 4460, 4461}, // Ardougne
        {4483, 4484, 4485, 4486}, // Desert
        {4462, 4463, 4464, 4465}, // Falador
        {4491, 4492, 4493, 4494}, // Fremennik
        {4475, 4476, 4477, 4478}, // Kandarin
        {3578, 3599, 3611, 4566}, // Karamja
        {7925, 7926, 7927, 7928}, // Kourend & Kebos
        {4495, 4496, 4497, 4498}, // Lumbridge & Draynor
        {4487, 4488, 4489, 4490}, // Morytania
        {4479, 4480, 4481, 4482}, // Varrock
        {4471, 4472, 4473, 4474}, // Western Provinces
        {4466, 4467, 4468, 4469}, // Wilderness
    };

    private static final String[] DIARY_TIERS = {"easy", "medium", "hard", "elite"};

    private PlayerContextBuilder()
    {
    }

    /**
     * Build a full player context snapshot. Must be called on the game thread.
     *
     * @param client the RuneLite Client instance
     * @return JsonObject with player data, or null if not logged in
     */
    public static JsonObject build(Client client)
    {
        if (client == null || client.getGameState() != GameState.LOGGED_IN)
        {
            return null;
        }

        Player localPlayer = client.getLocalPlayer();
        if (localPlayer == null)
        {
            return null;
        }

        JsonObject ctx = new JsonObject();

        // Account type
        if (client.getAccountType() != null)
        {
            ctx.addProperty("account_type", client.getAccountType().name());
        }

        // Player name
        String name = localPlayer.getName();
        if (name != null)
        {
            ctx.addProperty("player_name", name);
        }

        // Combat level
        ctx.addProperty("combat_level", localPlayer.getCombatLevel());

        // Skills (all 23, skip OVERALL)
        JsonObject skills = new JsonObject();
        int totalLevel = 0;
        for (Skill skill : Skill.values())
        {
            if (skill == Skill.OVERALL)
            {
                continue;
            }
            JsonObject skillData = new JsonObject();
            int level = client.getRealSkillLevel(skill);
            skillData.addProperty("level", level);
            skillData.addProperty("xp", client.getSkillExperience(skill));
            skills.add(skill.getName().toLowerCase(), skillData);
            totalLevel += level;
        }
        ctx.add("skills", skills);
        ctx.addProperty("total_level", totalLevel);

        // Quests
        JsonArray completed = new JsonArray();
        JsonArray inProgress = new JsonArray();
        for (Quest quest : Quest.values())
        {
            try
            {
                QuestState state = quest.getState(client);
                if (state == QuestState.FINISHED)
                {
                    completed.add(quest.getName());
                }
                else if (state == QuestState.IN_PROGRESS)
                {
                    inProgress.add(quest.getName());
                }
            }
            catch (Exception ignored)
            {
                // Some quests may not be queryable in all game states
            }
        }
        ctx.add("quests_completed", completed);
        ctx.add("quests_in_progress", inProgress);

        // Achievement diaries
        try
        {
            JsonObject diaries = buildDiaries(client);
            ctx.add("diaries", diaries);
        }
        catch (Exception ignored)
        {
            // Diary varbits may not be accessible
        }

        // Current location
        WorldPoint loc = localPlayer.getWorldLocation();
        if (loc != null)
        {
            JsonObject location = new JsonObject();
            location.addProperty("x", loc.getX());
            location.addProperty("y", loc.getY());
            location.addProperty("plane", loc.getPlane());
            ctx.add("location", location);
        }

        return ctx;
    }

    private static JsonObject buildDiaries(Client client)
    {
        JsonObject diaries = new JsonObject();
        for (int i = 0; i < DIARY_REGIONS.length; i++)
        {
            JsonObject region = new JsonObject();
            for (int t = 0; t < DIARY_TIERS.length; t++)
            {
                boolean done = client.getVarbitValue(DIARY_VARBITS[i][t]) >= 1;
                region.addProperty(DIARY_TIERS[t], done);
            }
            diaries.add(DIARY_REGIONS[i], region);
        }
        return diaries;
    }

    /**
     * Map AccountType name to a game_mode string matching the backend's expected values.
     */
    public static String accountTypeToGameMode(String accountType)
    {
        if (accountType == null)
        {
            return null;
        }
        switch (accountType)
        {
            case "IRONMAN":
                return "ironman";
            case "HARDCORE_IRONMAN":
                return "hardcore_ironman";
            case "ULTIMATE_IRONMAN":
                return "ultimate_ironman";
            case "GROUP_IRONMAN":
            case "HARDCORE_GROUP_IRONMAN":
            case "UNRANKED_GROUP_IRONMAN":
                return "group_ironman";
            case "NORMAL":
            default:
                return "main";
        }
    }
}
