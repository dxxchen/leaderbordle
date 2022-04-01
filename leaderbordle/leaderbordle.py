import discord
import os
import sys

from discord.ext import commands
from dotenv import load_dotenv
from storage import SupabaseStore
from variants import get_variants

load_dotenv()

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
variants = get_variants()

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
store = SupabaseStore(supabase_url, supabase_key)

medal_emojis = ['🥇', '🥈', '🥉']

@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(f'+ {guild.id} (name: {guild.name})')

@bot.event
async def on_message(message):
    was_parsed = False
    for variant in variants.values():
        result = variant.parse(message.content)
        if result is None:
            continue

        store.record_result(variant.name(), message.author.id, result)

        await message.add_reaction('🤖')

        was_parsed = True

    if not was_parsed:
        await bot.process_commands(message)

@bot.command()
async def listvariants(ctx):
    embed = discord.Embed()
    embed.title = 'Variants'
    embed.description = ''
    for variant in variants.values():
        embed.description += '\n**%s** %s' % (variant.linkified_title(), variant.info())

    await ctx.send(embed=embed)

@bot.command()
async def leaders(ctx, days=10):
    if (days < 1):
        await ctx.send('The number of days must be greater than or equal to 1.')
        return
    if (days > 30):
        await ctx.send('The number of days must be less than or equal to 30.')
        return

    leaders = store.read_leaders(days, [])
    if len(leaders) == 0:
        await ctx.send('There are no leaders. Play more!')
        return

    embed = discord.Embed()
    embed.title = 'Leaders (last %d day%s)' % (days, ('s' if days > 1 else ''))

    for variant_name, variant_leaders in leaders.items():
        field_message = ''
        medals_awarded = 0
        next_medal = 0
        num_tied = 1

        last_successes = sys.maxsize
        last_guesses = 0

        for user_id, data in variant_leaders.items():
            member = ctx.message.guild.get_member(user_id)
            if member is None:
                continue

            field_message += '%s **%s**\n⠀⠀ %d win%s / %.2f avg.\n' % (
                medal_emojis[next_medal],
                member.display_name,
                data['successes'],
                ('s' if data['successes'] > 1 else ''),
                data['avg_guesses'])

            medals_awarded += 1

            # Only move on to the next medal if the number of successes is lower or the number of
            # guesses is higher than the previous medal holder.
            if data['successes'] < last_successes or data['avg_guesses'] > last_guesses:
                # Terminate the loop if all tied users have been awarded medals and there have
                # been at least 3 medals awarded.
                if medals_awarded > 2:
                    break

                last_successes = data['successes']
                last_guesses = data['last_guesses']

                next_medal += num_tied
                num_tied = 1
            else:
                num_tied += 1

        if medals_awarded == 0:
            continue

        embed.add_field(
            name=variants[variant_name].title(),
            value=field_message,
            inline=True)

    await ctx.send(embed=embed)

@bot.group()
async def stats(ctx):
    pass

@stats.command()
async def me(ctx):
    await user(ctx, ctx.message.author)

@stats.command()
async def user(ctx, user: discord.Member):
    stats = store.read_user_stats(user.id)
    if len(stats) == 0:
        await ctx.send('**%s** has no *dle stats. Play more!' % user.display_name)
        return

    embed = discord.Embed()
    embed.title = 'Stats for %s' % user.display_name

    for variant_name, variant_stats in stats.items():
        embed.add_field(
            name=variants[variant_name].title(),
            value=
                'Attempts: %d/%d (%.f%%)\n' % (variant_stats.successes, variant_stats.attempts, variant_stats.successes / variant_stats.attempts * 100)
                    + 'Avg. guesses: %.2f' % (sum(k * v for k, v in variant_stats.distribution.items()) / sum(v for v in variant_stats.distribution.values())),
            inline=True)

    await ctx.send(embed=embed)

bot_token = os.getenv('BOT_TOKEN')
bot.run(bot_token)
