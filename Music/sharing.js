/* Private sharing between signed-in music accounts. */
class MusicSharingController {
    constructor(app) {
        this.app = app;
        this.sendModal = document.getElementById('musicShareModal');
        this.inboxModal = document.getElementById('musicSharesModal');
        this.form = document.getElementById('musicShareForm');
        this.recipient = document.getElementById('musicShareRecipient');
        this.error = document.getElementById('musicShareError');
        this.sendButton = document.getElementById('musicShareSend');
        this.list = document.getElementById('musicSharesList');
        this.moreButton = document.getElementById('musicSharesMore');
        this.refreshButton = document.getElementById('musicSharesRefresh');
        this.offset = 0;
        this.generation = 0;
        this.loading = false;
        this.sending = false;

        this.form.addEventListener('submit', event => {
            event.preventDefault();
            this.send();
        });
        document.getElementById('btnFavShare').addEventListener('click', () => this.openFavorites());
        document.querySelectorAll('[data-open-music-shares]').forEach(button => {
            button.addEventListener('click', () => this.openInbox());
        });
        this.moreButton.addEventListener('click', () => this.loadInbox(false));
        this.refreshButton.addEventListener('click', () => this.loadInbox(true));
        for (const modal of [this.sendModal, this.inboxModal]) {
            modal.querySelector('.modal-close').addEventListener('click', () => this.close(modal));
            modal.addEventListener('click', event => {
                if (event.target === modal) this.close(modal);
            });
            modal.addEventListener('keydown', event => {
                if (event.key === 'Escape') {
                    event.stopPropagation();
                    this.close(modal);
                } else if (event.key === 'Tab') {
                    const controls = [...modal.querySelectorAll('button:not(:disabled), input:not(:disabled)')]
                        .filter(control => control.getClientRects().length && !control.hidden);
                    const first = controls[0];
                    const last = controls[controls.length - 1];
                    if (event.shiftKey && document.activeElement === first) {
                        event.preventDefault();
                        last?.focus();
                    } else if (!event.shiftKey && document.activeElement === last) {
                        event.preventDefault();
                        first?.focus();
                    }
                }
            });
        }
    }

    close(modal) {
        this.app.closeModal(modal);
        const trigger = modal === this.sendModal ? this.sendTrigger : this.inboxTrigger;
        if (trigger?.isConnected) trigger.focus();
    }

    reset() {
        this.generation++;
        this.selection = null;
        this.list.replaceChildren();
        this.error.textContent = '';
        this.recipient.value = '';
        this.offset = 0;
        this.loading = false;
        this.sending = false;
        this.sendButton.disabled = false;
        this.moreButton.disabled = this.refreshButton.disabled = false;
        this.moreButton.hidden = true;
        this.sendModal.classList.remove('open');
        this.inboxModal.classList.remove('open');
    }

    async request(path = '', options = {}) {
        const generation = this.generation;
        const response = await fetch(`/api/music/user/shares${path}`, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...options.headers },
        });
        const data = await response.json();
        if (generation !== this.generation) throw new Error('Phiên đăng nhập đã thay đổi.');
        if (!response.ok || data.status !== 'success') {
            throw new Error(typeof data.detail === 'string' ? data.detail : (data.message || 'Không thể thực hiện chia sẻ. Vui lòng thử lại.'));
        }
        return data;
    }

    open(selection, title) {
        if (!this.app.currentUser) return this.app.openAuthModal();
        if (this.sending) return;
        this.selection = selection;
        this.sendTrigger = document.activeElement;
        document.getElementById('musicShareTitle').textContent = title;
        this.recipient.value = '';
        this.error.textContent = '';
        this.app.openModal(this.sendModal);
        requestAnimationFrame(() => this.recipient.focus());
    }

    openPlaylist(playlist) {
        if (!playlist.tracks?.length) return this.app.showToast('Playlist chưa có bài hát để chia sẻ.');
        this.open({ kind: 'playlist', playlist_id: playlist.id }, playlist.name);
    }

    openFavorites(favorite = null) {
        if (!this.app.favoriteTracks?.length) return this.app.showToast('Danh sách yêu thích đang trống.');
        const selection = { kind: 'favorites' };
        if (favorite) {
            selection.favorite = {
                chat_id: String(favorite.chat_id || favorite.chatId || ''),
                msg_id: String(favorite.msg_id || favorite.msgId || ''),
                title: favorite.title || favorite.name || '',
                artist: favorite.artist || '',
            };
        }
        this.open(selection, favorite ? (favorite.title || favorite.name) : `Bài hát yêu thích (${this.app.favoriteTracks.length} bài)`);
    }

    async send() {
        if (this.sending || !this.selection) return;
        const recipient = this.recipient.value.trim().replace(/^@/, '').trim();
        if (!recipient) {
            this.error.textContent = 'Vui lòng nhập tên đăng nhập của người nhận.';
            this.recipient.focus();
            return;
        }
        const generation = this.generation;
        this.sending = true;
        this.sendButton.disabled = true;
        this.error.textContent = '';
        try {
            const data = await this.request('', { method: 'POST', body: JSON.stringify({ ...this.selection, recipient }) });
            this.close(this.sendModal);
            this.app.showToast(data.message);
        } catch (error) {
            if (generation === this.generation) this.error.textContent = error.message;
        } finally {
            if (generation === this.generation) {
                this.sending = false;
                this.sendButton.disabled = false;
            }
        }
    }

    openInbox() {
        if (!this.app.currentUser) return this.app.openAuthModal();
        this.inboxTrigger = document.activeElement;
        this.app.openModal(this.inboxModal);
        requestAnimationFrame(() => this.inboxModal.querySelector('.modal-close').focus());
        return this.loadInbox(true);
    }

    async loadInbox(reset) {
        if (this.loading) return;
        const generation = this.generation;
        this.loading = true;
        this.moreButton.disabled = this.refreshButton.disabled = true;
        const status = document.getElementById('musicSharesStatus');
        if (reset) {
            this.offset = 0;
            this.list.replaceChildren();
            this.moreButton.hidden = true;
        }
        status.textContent = 'Đang tải nội dung được chia sẻ…';
        try {
            const data = await this.request(`?offset=${this.offset}`);
            data.shares.forEach(share => this.renderShare(share));
            this.offset += data.shares.length;
            this.moreButton.hidden = !data.has_more;
            status.textContent = this.offset ? '' : 'Chưa có nội dung được chia sẻ. Nhờ bạn bè gửi playlist hoặc bài hát đến tên đăng nhập của bạn.';
        } catch (error) {
            if (generation === this.generation) status.textContent = error.message;
        } finally {
            if (generation === this.generation) {
                this.loading = false;
                this.moreButton.disabled = this.refreshButton.disabled = false;
            }
        }
    }

    renderShare(share) {
        const item = document.createElement('article');
        item.className = 'music-share-card';
        const title = document.createElement('h4');
        title.textContent = share.title;
        const meta = document.createElement('p');
        meta.textContent = `${share.sender_name} đã chia sẻ • ${share.track_count} bài • ${new Date(share.created_at * 1000).toLocaleDateString('vi-VN')}`;
        const actions = document.createElement('div');
        actions.className = 'music-share-actions';
        const tracks = document.createElement('ol');
        tracks.className = 'music-share-tracks';
        tracks.hidden = true;
        const feedback = document.createElement('p');
        feedback.setAttribute('role', 'status');
        item.append(title, meta, actions, feedback, tracks);
        const path = `/${encodeURIComponent(share.id)}`;
        const addAction = (label, handler) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'pl-action-badge blue-badge';
            button.textContent = label;
            button.addEventListener('click', async () => {
                const generation = this.generation;
                button.disabled = true;
                try { await handler(button); }
                catch (error) {
                    if (generation === this.generation) {
                        feedback.textContent = error.message;
                        this.app.showToast(error.message);
                    }
                }
                finally { button.disabled = false; }
            });
            actions.appendChild(button);
        };
        addAction('Phát', async () => {
            const { share: detail } = await this.request(path);
            this.app.playPlaylist({ id: `received_${share.id}`, name: detail.title, tracks: detail.tracks });
            this.close(this.inboxModal);
            this.app.closeModal(this.app.playlistModal);
            this.app.closeModal(this.app.favoritesModal);
        });
        addAction('Xem bài hát', async button => {
            if (!tracks.hidden) {
                tracks.hidden = true;
                button.textContent = 'Xem bài hát';
                return;
            }
            const { share: detail } = await this.request(path);
            tracks.replaceChildren();
            detail.tracks.forEach(track => {
                const row = document.createElement('li');
                row.textContent = `${track.name}${track.artist ? ` • ${track.artist}` : ''}`;
                tracks.appendChild(row);
            });
            tracks.hidden = false;
            button.textContent = 'Thu gọn';
        });
        for (const [destination, label] of [['playlist', 'Lưu playlist'], ['favorites', 'Thêm vào yêu thích']]) {
            addAction(label, async () => {
                const data = await this.request(`${path}/import`, { method: 'POST', body: JSON.stringify({ destination }) });
                feedback.textContent = data.message;
                this.app.showToast(data.message);
                if (destination === 'playlist') await this.app.loadPlaylists();
                else {
                    await this.app.fetchUserFavorites();
                    this.app.renderFavoritesList();
                }
            });
        }
        addAction('Bỏ khỏi danh sách', async () => {
            if (!confirm(`Bỏ "${share.title}" khỏi mục được chia sẻ? Playlist và yêu thích đã lưu vẫn được giữ.`)) return;
            await this.request(path, { method: 'DELETE' });
            // Reload so subsequent pagination cannot skip a row after deletion.
            await this.loadInbox(true);
        });
        this.list.appendChild(item);
    }
}
