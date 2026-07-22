from __future__ import annotations

from app.streaming import Broadcaster


async def test_publish_fans_out_to_all_subscribers() -> None:
    broadcaster = Broadcaster()

    async with broadcaster.subscribe() as q1, broadcaster.subscribe() as q2:
        await broadcaster.publish({"seq": 1})

        assert await q1.get() == {"seq": 1}
        assert await q2.get() == {"seq": 1}


async def test_publish_with_no_subscribers_is_a_noop() -> None:
    broadcaster = Broadcaster()

    await broadcaster.publish({"seq": 1})


async def test_subscribe_registers_and_unsubscribe_removes_on_exit() -> None:
    broadcaster = Broadcaster()

    assert broadcaster.subscriber_count == 0

    async with broadcaster.subscribe():
        assert broadcaster.subscriber_count == 1

    assert broadcaster.subscriber_count == 0


async def test_unsubscribed_queue_receives_nothing_published_afterwards() -> None:
    broadcaster = Broadcaster()

    async with broadcaster.subscribe() as queue:
        pass

    await broadcaster.publish({"seq": 1})
    assert queue.empty()


async def test_full_queue_drops_new_messages_instead_of_blocking() -> None:
    broadcaster = Broadcaster(maxsize=2)

    async with broadcaster.subscribe() as queue:
        for i in range(5):
            await broadcaster.publish({"seq": i})

        assert queue.full()
        assert queue.qsize() == 2
        assert await queue.get() == {"seq": 0}
        assert await queue.get() == {"seq": 1}
        assert queue.empty()


async def test_one_subscriber_full_queue_does_not_affect_others() -> None:
    broadcaster = Broadcaster(maxsize=1)

    async with broadcaster.subscribe() as slow, broadcaster.subscribe() as fast:
        await broadcaster.publish({"seq": 0})
        assert await fast.get() == {"seq": 0}

        # slow's queue is still full of {"seq": 0} at this point, so this
        # publish is dropped for slow but must still reach fast.
        await broadcaster.publish({"seq": 1})

        assert slow.qsize() == 1
        assert await slow.get() == {"seq": 0}
        assert await fast.get() == {"seq": 1}
