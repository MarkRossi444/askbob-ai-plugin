package com.wiseoldman;

import com.google.gson.JsonObject;
import com.wiseoldman.api.WiseOldManApiClient;

import java.awt.*;
import java.util.ArrayList;
import java.util.List;
import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.text.DefaultCaret;

import net.runelite.client.ui.ColorScheme;
import net.runelite.client.ui.PluginPanel;

public class WiseOldManPanel extends PluginPanel
{
    private static final Color GOLD = new Color(255, 215, 0);
    private static final Color DARK_BG = new Color(27, 27, 27);
    private static final Color DARKER_BG = new Color(20, 20, 20);
    private static final Color USER_BG = new Color(45, 42, 36);
    private static final Color BOT_BG = new Color(30, 28, 24);
    private static final Color BORDER_COLOR = new Color(60, 55, 45);
    private static final Color TEXT_COLOR = new Color(190, 185, 175);
    private static final Color INPUT_BG = new Color(35, 33, 28);

    private static final int MAX_HISTORY_MESSAGES = 20;
    private static final int CONTEXT_WINDOW_SIZE = 10;

    private final JPanel chatArea;
    private final JTextField inputField;
    private final JButton sendButton;
    private final JScrollPane chatScrollPane;
    private final WiseOldManConfig config;
    private final List<JsonObject> conversationHistory = new ArrayList<>();

    private WiseOldManApiClient apiClient;
    private JTextArea activeBotTextArea;
    private boolean isRequestInProgress;

    public WiseOldManPanel(WiseOldManConfig config)
    {
        super(false);
        this.config = config;

        setLayout(new BorderLayout());
        setBackground(DARK_BG);

        // Header
        JPanel headerPanel = new JPanel(new BorderLayout());
        headerPanel.setBackground(DARKER_BG);
        headerPanel.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createMatteBorder(0, 0, 1, 0, BORDER_COLOR),
            new EmptyBorder(8, 10, 8, 10)
        ));

        JLabel titleLabel = new JLabel("WiseOldMan.Ai");
        titleLabel.setForeground(GOLD);
        titleLabel.setFont(titleLabel.getFont().deriveFont(Font.BOLD, 13f));
        headerPanel.add(titleLabel, BorderLayout.WEST);

        JLabel modeLabel = new JLabel(config.gameMode().toString());
        modeLabel.setForeground(new Color(120, 115, 105));
        modeLabel.setFont(modeLabel.getFont().deriveFont(11f));
        headerPanel.add(modeLabel, BorderLayout.EAST);

        add(headerPanel, BorderLayout.NORTH);

        // Chat area
        chatArea = new JPanel();
        chatArea.setLayout(new BoxLayout(chatArea, BoxLayout.Y_AXIS));
        chatArea.setBackground(DARK_BG);
        chatArea.setBorder(new EmptyBorder(5, 0, 5, 0));

        chatScrollPane = new JScrollPane(chatArea);
        chatScrollPane.setBackground(DARK_BG);
        chatScrollPane.getViewport().setBackground(DARK_BG);
        chatScrollPane.setBorder(null);
        chatScrollPane.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED);
        chatScrollPane.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);

        add(chatScrollPane, BorderLayout.CENTER);

        // Input area
        JPanel inputPanel = new JPanel(new BorderLayout(4, 0));
        inputPanel.setBackground(DARKER_BG);
        inputPanel.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createMatteBorder(1, 0, 0, 0, BORDER_COLOR),
            new EmptyBorder(8, 8, 8, 8)
        ));

        inputField = new JTextField();
        inputField.setBackground(INPUT_BG);
        inputField.setForeground(TEXT_COLOR);
        inputField.setCaretColor(GOLD);
        inputField.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(BORDER_COLOR, 1),
            new EmptyBorder(5, 8, 5, 8)
        ));
        inputField.setFont(inputField.getFont().deriveFont(12f));
        inputField.addActionListener(e -> sendMessage());

        sendButton = new JButton("Ask");
        sendButton.setBackground(new Color(180, 155, 50));
        sendButton.setForeground(Color.BLACK);
        sendButton.setFocusPainted(false);
        sendButton.setBorderPainted(false);
        sendButton.setFont(sendButton.getFont().deriveFont(Font.BOLD, 11f));
        sendButton.setPreferredSize(new Dimension(50, 28));
        sendButton.addActionListener(e -> sendMessage());

        inputPanel.add(inputField, BorderLayout.CENTER);
        inputPanel.add(sendButton, BorderLayout.EAST);

        add(inputPanel, BorderLayout.SOUTH);

        // Welcome message
        addBotMessage("Greetings, adventurer. Ask me anything about Old School RuneScape.");
    }

    public void setApiClient(WiseOldManApiClient apiClient)
    {
        this.apiClient = apiClient;
    }

    private void sendMessage()
    {
        if (isRequestInProgress)
        {
            return;
        }

        String message = inputField.getText().trim();
        if (message.isEmpty())
        {
            return;
        }

        isRequestInProgress = true;
        addUserMessage(message);
        inputField.setText("");
        inputField.setEnabled(false);
        sendButton.setEnabled(false);

        // Add user message to conversation history
        JsonObject userMsg = new JsonObject();
        userMsg.addProperty("role", "user");
        userMsg.addProperty("content", message);
        conversationHistory.add(userMsg);
        trimHistory();

        // Show typing indicator — store text area reference directly
        activeBotTextArea = createBotMessageWithRef("Thinking...");
        activeBotTextArea.setForeground(new Color(120, 115, 105));
        chatArea.revalidate();
        scrollToBottom();

        if (apiClient == null)
        {
            updateBotMessage("API not connected. Check plugin settings.");
            onResponseComplete();
            return;
        }

        // Send last N messages as context
        List<JsonObject> context = getRecentHistory();

        String gameMode = config.gameMode().name().toLowerCase();
        apiClient.askQuestion(message, gameMode, context, new WiseOldManApiClient.ApiCallback()
        {
            @Override
            public void onSuccess(String answer)
            {
                SwingUtilities.invokeLater(() -> {
                    updateBotMessage(answer);

                    // Add assistant response to history
                    JsonObject assistantMsg = new JsonObject();
                    assistantMsg.addProperty("role", "assistant");
                    assistantMsg.addProperty("content", answer);
                    conversationHistory.add(assistantMsg);
                    trimHistory();

                    onResponseComplete();
                });
            }

            @Override
            public void onError(String error)
            {
                SwingUtilities.invokeLater(() -> {
                    updateBotMessage("Error: " + error);
                    // Remove the failed user message from history
                    if (!conversationHistory.isEmpty())
                    {
                        JsonObject last = conversationHistory.get(conversationHistory.size() - 1);
                        if ("user".equals(last.get("role").getAsString()))
                        {
                            conversationHistory.remove(conversationHistory.size() - 1);
                        }
                    }
                    onResponseComplete();
                });
            }
        });
    }

    private void trimHistory()
    {
        while (conversationHistory.size() > MAX_HISTORY_MESSAGES)
        {
            conversationHistory.remove(0);
        }
    }

    private List<JsonObject> getRecentHistory()
    {
        int size = conversationHistory.size();
        if (size <= CONTEXT_WINDOW_SIZE)
        {
            return new ArrayList<>(conversationHistory);
        }
        return new ArrayList<>(conversationHistory.subList(size - CONTEXT_WINDOW_SIZE, size));
    }

    private void updateBotMessage(String message)
    {
        if (activeBotTextArea != null)
        {
            activeBotTextArea.setText(message);
            activeBotTextArea.setForeground(TEXT_COLOR);
            activeBotTextArea = null;
            chatArea.revalidate();
            scrollToBottom();
        }
    }

    private void onResponseComplete()
    {
        isRequestInProgress = false;
        inputField.setEnabled(true);
        sendButton.setEnabled(true);
        inputField.requestFocusInWindow();
    }

    private void addUserMessage(String message)
    {
        JPanel panel = new JPanel(new BorderLayout());
        panel.setBackground(DARK_BG);
        panel.setBorder(new EmptyBorder(2, 30, 2, 8));
        panel.setMaximumSize(new Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE));

        JPanel inner = new JPanel(new BorderLayout());
        inner.setBackground(USER_BG);
        inner.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(BORDER_COLOR, 1),
            new EmptyBorder(6, 8, 6, 8)
        ));

        JTextArea textArea = new JTextArea(message);
        textArea.setWrapStyleWord(true);
        textArea.setLineWrap(true);
        textArea.setEditable(false);
        textArea.setFont(textArea.getFont().deriveFont(12f));
        textArea.setBackground(USER_BG);
        textArea.setForeground(new Color(220, 215, 205));
        textArea.setBorder(null);

        inner.add(textArea, BorderLayout.CENTER);
        panel.add(inner, BorderLayout.CENTER);

        chatArea.add(panel);
        chatArea.add(Box.createVerticalStrut(4));
        chatArea.revalidate();
        scrollToBottom();
    }

    private void addBotMessage(String message)
    {
        createBotMessageWithRef(message);
        chatArea.revalidate();
        scrollToBottom();
    }

    /**
     * Creates a bot message panel, adds it to the chat area, and returns
     * a direct reference to the JTextArea for safe updates.
     */
    private JTextArea createBotMessageWithRef(String message)
    {
        JPanel panel = new JPanel(new BorderLayout());
        panel.setBackground(DARK_BG);
        panel.setBorder(new EmptyBorder(2, 8, 2, 30));
        panel.setMaximumSize(new Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE));

        JPanel inner = new JPanel(new BorderLayout());
        inner.setBackground(BOT_BG);
        inner.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(new Color(50, 48, 40), 1),
            new EmptyBorder(6, 8, 6, 8)
        ));

        JTextArea textArea = new JTextArea(message);
        textArea.setWrapStyleWord(true);
        textArea.setLineWrap(true);
        textArea.setEditable(false);
        textArea.setFont(textArea.getFont().deriveFont(12f));
        textArea.setBackground(BOT_BG);
        textArea.setForeground(TEXT_COLOR);
        textArea.setBorder(null);

        // Auto-scroll caret
        DefaultCaret caret = (DefaultCaret) textArea.getCaret();
        caret.setUpdatePolicy(DefaultCaret.ALWAYS_UPDATE);

        inner.add(textArea, BorderLayout.CENTER);
        panel.add(inner, BorderLayout.CENTER);

        chatArea.add(panel);
        chatArea.add(Box.createVerticalStrut(4));

        return textArea;
    }

    private void scrollToBottom()
    {
        SwingUtilities.invokeLater(() -> {
            JScrollBar vertical = chatScrollPane.getVerticalScrollBar();
            vertical.setValue(vertical.getMaximum());
        });
    }
}
