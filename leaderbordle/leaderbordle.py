import discord
import os

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
store = SupabaseStore(variants, supabase_url, supabase_key)

variant_emojis = {v.name() : v.emoji() for v in variants}
medal_emojis = ['🥇', '🥈', '🥉']

@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(f'+ {guild.id} (name: {guild.name})')

@bot.event
async def on_message(message):
    was_parsed = False
    for variant in variants:
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
    for variant in variants:
        embed.description += '\n**[' + variant.name() + '](' + variant.url() + ")** \t" + variant.info()

    await ctx.send(embed=embed)

@bot.command()
async def leaders(ctx, days=10):
    leaders = store.read_leaders(days, [])
    if len(leaders) == 0:
        await ctx.send('There are no leaders. Play more!')
        return

    embed = discord.Embed()
    embed.title = f'Leaders (last {days} days)'

    for variant_name, variant_leaders in leaders.items():
        field_message = ''
        for i in range(0, min(3, len(variant_leaders))):
            user_id, data = list(variant_leaders.items())[i]

            member = ctx.message.guild.get_member(user_id)
            if member is None:
                continue

            field_message += '%s **%s**\n⠀⠀ %d win%s / %.2f avg.\n' % (medal_emojis[i], member.display_name, data['successes'], ('s' if data['successes'] > 1 else ''), data['avg_guesses'])

        if field_message == '':
            continue

        embed.add_field(
            name=variant_emojis[variant_name] + ' ' + variant_name,
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
        print(variant_stats.distribution)
        embed.add_field(
            name=variant_emojis[variant_name] + ' ' + variant_name,
            value=
                'Attempts: %d/%d (%.f%%)\n' % (variant_stats.successes, variant_stats.attempts, variant_stats.successes / variant_stats.attempts * 100)
                    + 'Avg. guesses: %.2f' % (sum(k * v for k, v in variant_stats.distribution.items()) / sum(v for v in variant_stats.distribution.values())),
            inline=True)

    await ctx.send(embed=embed)

bot_token = os.getenv('BOT_TOKEN')
bot.run(bot_token)
