# -*- coding: utf-8 -*-
import structlog

from raiden.messages import (
    message_from_sendevent,
    Lock,
)
from raiden.transfer.events import (
    ContractSendChannelClose,
    ContractSendChannelSettle,
    ContractSendChannelUpdateTransfer,
    ContractSendChannelWithdraw,
    EventTransferReceivedSuccess,
    EventTransferSentFailed,
    EventTransferSentSuccess,
    SendDirectTransfer,
    SendProcessed,
)
from raiden.transfer.mediated_transfer.events import (
    EventUnlockFailed,
    EventUnlockSuccess,
    EventWithdrawFailed,
    EventWithdrawSuccess,
    SendBalanceProof,
    SendLockedTransfer,
    SendRefundTransfer,
    SendRevealSecret,
    SendSecretRequest,
)
from raiden.utils import pex

log = structlog.get_logger(__name__)  # pylint: disable=invalid-name
UNEVENTFUL_EVENTS = (
    EventTransferReceivedSuccess,
    EventUnlockSuccess,
    EventWithdrawFailed,
    EventWithdrawSuccess,
)


def handle_send_lockedtransfer(
        raiden: 'RaidenService',
        send_locked_transfer: SendLockedTransfer,
):
    mediated_transfer_message = message_from_sendevent(send_locked_transfer, raiden.address)
    raiden.sign(mediated_transfer_message)
    raiden.protocol.send_async(
        mediated_transfer_message.recipient,
        send_locked_transfer.queue_name,
        mediated_transfer_message,
    )


def handle_send_directtransfer(
        raiden: 'RaidenService',
        send_direct_transfer: SendDirectTransfer,
):
    direct_transfer_message = message_from_sendevent(send_direct_transfer, raiden.address)
    raiden.sign(direct_transfer_message)
    raiden.protocol.send_async(
        send_direct_transfer.recipient,
        send_direct_transfer.queue_name,
        direct_transfer_message,
    )


def handle_send_revealsecret(
        raiden: 'RaidenService',
        reveal_secret_event: SendRevealSecret,
):
    reveal_secret_message = message_from_sendevent(reveal_secret_event, raiden.address)
    raiden.sign(reveal_secret_message)
    raiden.protocol.send_async(
        reveal_secret_event.recipient,
        reveal_secret_event.queue_name,
        reveal_secret_message,
    )


def handle_send_balanceproof(
        raiden: 'RaidenService',
        balance_proof_event: SendBalanceProof,
):
    secret_message = message_from_sendevent(balance_proof_event, raiden.address)
    raiden.sign(secret_message)
    raiden.protocol.send_async(
        balance_proof_event.recipient,
        balance_proof_event.queue_name,
        secret_message,
    )


def handle_send_secretrequest(
        raiden: 'RaidenService',
        secret_request_event: SendSecretRequest,
):
    secret_request_message = message_from_sendevent(secret_request_event, raiden.address)
    raiden.sign(secret_request_message)
    raiden.protocol.send_async(
        secret_request_event.recipient,
        secret_request_event.queue_name,
        secret_request_message,
    )


def handle_send_refundtransfer(
        raiden: 'RaidenService',
        refund_transfer_event: SendRefundTransfer,
):
    refund_transfer_message = message_from_sendevent(refund_transfer_event, raiden.address)
    raiden.sign(refund_transfer_message)
    raiden.protocol.send_async(
        refund_transfer_event.recipient,
        refund_transfer_event.queue_name,
        refund_transfer_message,
    )


def handle_send_processed(
        raiden: 'RaidenService',
        processed_event: SendProcessed,
):
    processed_message = message_from_sendevent(processed_event, raiden.address)
    raiden.sign(processed_message)
    raiden.protocol.send_async(
        processed_event.recipient,
        processed_event.queue_name,
        processed_message,
    )


def handle_transfersentsuccess(
        raiden: 'RaidenService',
        transfer_sent_success_event: EventTransferSentSuccess
):
    for result in raiden.identifier_to_results[transfer_sent_success_event.identifier]:
        result.set(True)

    del raiden.identifier_to_results[transfer_sent_success_event.identifier]


def handle_transfersentfailed(
        raiden: 'RaidenService',
        transfer_sent_failed_event: EventTransferSentFailed
):
    for result in raiden.identifier_to_results[transfer_sent_failed_event.identifier]:
        result.set(False)
    del raiden.identifier_to_results[transfer_sent_failed_event.identifier]


def handle_unlockfailed(
        raiden: 'RaidenService',
        unlock_failed_event: EventUnlockFailed
):
    # pylint: disable=unused-argument
    log.error(
        'UnlockFailed!',
        secrethash=pex(unlock_failed_event.secrethash),
        reason=unlock_failed_event.reason
    )


def handle_contract_channelclose(
        raiden: 'RaidenService',
        channel_close_event: ContractSendChannelClose
):
    balance_proof = channel_close_event.balance_proof

    if balance_proof:
        nonce = balance_proof.nonce
        transferred_amount = balance_proof.transferred_amount
        locksroot = balance_proof.locksroot
        signature = balance_proof.signature
        message_hash = balance_proof.message_hash

    else:
        nonce = 0
        transferred_amount = 0
        locksroot = b''
        signature = b''
        message_hash = b''

    channel = raiden.chain.netting_channel(channel_close_event.channel_identifier)

    channel.close(
        nonce,
        transferred_amount,
        locksroot,
        message_hash,
        signature,
    )


def handle_contract_channelupdate(
        raiden: 'RaidenService',
        channel_update_event: ContractSendChannelUpdateTransfer
):
    balance_proof = channel_update_event.balance_proof

    if balance_proof:
        channel = raiden.chain.netting_channel(channel_update_event.channel_identifier)
        channel.update_transfer(
            balance_proof.nonce,
            balance_proof.transferred_amount,
            balance_proof.locksroot,
            balance_proof.message_hash,
            balance_proof.signature,
        )


def handle_contract_channelwithdraw(
        raiden: 'RaidenService',
        channel_withdraw_event: ContractSendChannelWithdraw
):
    channel = raiden.chain.netting_channel(channel_withdraw_event.channel_identifier)
    block_number = raiden.get_block_number()

    for unlock_proof in channel_withdraw_event.unlock_proofs:
        lock = Lock.from_bytes(unlock_proof.lock_encoded)

        if lock.expiration < block_number:
            log.error('Lock has expired!', lock=lock)
        else:
            channel.withdraw(unlock_proof)


def handle_contract_channelsettle(
        raiden: 'RaidenService',
        channel_settle_event: ContractSendChannelSettle
):
    channel = raiden.chain.netting_channel(channel_settle_event.channel_identifier)
    channel.settle()


def on_raiden_event(raiden: 'RaidenService', event: 'Event'):
    # pylint: disable=too-many-branches

    if type(event) == SendLockedTransfer:
        handle_send_lockedtransfer(raiden, event)
    elif type(event) == SendDirectTransfer:
        handle_send_directtransfer(raiden, event)
    elif type(event) == SendRevealSecret:
        handle_send_revealsecret(raiden, event)
    elif type(event) == SendBalanceProof:
        handle_send_balanceproof(raiden, event)
    elif type(event) == SendSecretRequest:
        handle_send_secretrequest(raiden, event)
    elif type(event) == SendRefundTransfer:
        handle_send_refundtransfer(raiden, event)
    elif type(event) == SendProcessed:
        handle_send_processed(raiden, event)
    elif type(event) == EventTransferSentSuccess:
        handle_transfersentsuccess(raiden, event)
    elif type(event) == EventTransferSentFailed:
        handle_transfersentfailed(raiden, event)
    elif type(event) == EventUnlockFailed:
        handle_unlockfailed(raiden, event)
    elif type(event) == ContractSendChannelClose:
        handle_contract_channelclose(raiden, event)
    elif type(event) == ContractSendChannelUpdateTransfer:
        handle_contract_channelupdate(raiden, event)
    elif type(event) == ContractSendChannelWithdraw:
        handle_contract_channelwithdraw(raiden, event)
    elif type(event) == ContractSendChannelSettle:
        handle_contract_channelsettle(raiden, event)
    elif type(event) in UNEVENTFUL_EVENTS:
        pass
    else:
        log.error('Unknown event {}'.format(type(event)))
