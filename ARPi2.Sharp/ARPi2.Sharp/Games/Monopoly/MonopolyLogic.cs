using System;
using System.Collections.Generic;
using System.Linq;

namespace ARPi2.Sharp.Games.Monopoly;

/// <summary>Core Monopoly game rules — mirrors Python logic.py.</summary>
public static class MonopolyLogic
{
    private static double Now => Environment.TickCount64 / 1000.0;

    public static void MovePlayer(MonopolyPlayer player, int spaces)
    {
        int old = player.Position;
        player.MoveFrom = old;
        player.MovePath.Clear();
        for (int i = 1; i <= Math.Abs(spaces); i++)
        {
            int next = spaces > 0 ? (old + i) % 40 : ((old - i) % 40 + 40) % 40;
            player.MovePath.Add(next);
        }
        player.IsMoving = true;
        player.MoveStart = Now;
    }

    public static bool CheckPassedGo(MonopolyPlayer player) =>
        player.MoveFrom > player.Position && player.MovePath.Count > 0;

    public static void SendToJail(MonopolyPlayer player)
    {
        player.Position = MonopolyData.JailPosition;
        player.InJail = true;
        player.JailTurns = 0;
        player.ConsecutiveDoubles = 0;
        player.MovePath.Clear();
    }

    public static CardData DrawCard(string deckType,
        List<CardData> chanceDeck,
        List<CardData> communityDeck,
        Random? rng = null)
    {
        rng ??= new Random();
        if (deckType == "chance")
        {
            if (chanceDeck.Count == 0)
            {
                chanceDeck.AddRange(MonopolyData.GetChanceCards());
                Shuffle(chanceDeck, rng);
            }
            var card = chanceDeck[0];
            chanceDeck.RemoveAt(0);
            return card;
        }
        else
        {
            if (communityDeck.Count == 0)
            {
                communityDeck.AddRange(MonopolyData.GetCommunityChestCards());
                Shuffle(communityDeck, rng);
            }
            var card = communityDeck[0];
            communityDeck.RemoveAt(0);
            return card;
        }
    }

    public static int CalculateRent(Property space, int? diceRoll,
        MonopolyPlayer owner, List<Property> properties)
    {
        string? group = space.Data.Group;
        int ownedInGroup = 1;
        if (group is "Railroad" or "Utility")
            ownedInGroup = owner.Properties.Count(i => i >= 0 && i < properties.Count && properties[i].Data.Group == group);

        int rent = space.GetRent(diceRoll, ownedInGroup);

        if (group != null && group is not "Railroad" and not "Utility")
        {
            if (owner.HasMonopoly(group, properties) && space.Houses == 0)
                rent *= 2;
        }

        return rent;
    }

    public static void Shuffle<T>(List<T> list, Random rng)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }
    }
}
